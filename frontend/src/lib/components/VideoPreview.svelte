<script>
  import { onMount, onDestroy, afterUpdate } from 'svelte';
  import { currentProject } from '../stores/projectStore';
  import { videoState } from '../stores/videoPlayerStore';
  // activeCaption and activeWord will now be calculated within the canvas rendering logic
  // import { activeCaption, activeWord } from '../stores/derivedStores'; // No longer directly used here
  // import { getContext } from 'svelte'; // Not needed for now

  let videoElement;
  let canvasElement;
  let ctx;
  let animationFrame;
  let videoWidth = 1080; // Default resolution for canvas
  let videoHeight = 1920; // Default resolution for canvas

  let project = $currentProject;
  let video = $videoState;

  // Reactive declarations for current project and video state
  $: project = $currentProject;
  $: video = $videoState;
  $: {
    if (project?.resolution) {
      [videoWidth, videoHeight] = project.resolution.split('x').map(Number);
      if (canvasElement) {
        canvasElement.width = videoWidth;
        canvasElement.height = videoHeight;
        drawCaptions();
      }
    }
  }

  onMount(() => {
    ctx = canvasElement.getContext('2d');
    
    // Set canvas dimensions to match video resolution
    canvasElement.width = videoWidth;
    canvasElement.height = videoHeight;

    // Listen for timeline seek events
    window.addEventListener('timeline-seek', handleTimelineSeek);
    
    if (videoElement) {
      videoElement.addEventListener('timeupdate', handleTimeUpdate);
      videoElement.addEventListener('loadedmetadata', handleMetadata);
      videoElement.addEventListener('play', () => videoState.setPlaying(true));
      videoElement.addEventListener('pause', () => videoState.setPlaying(false));
      videoElement.addEventListener('seeked', drawCaptions); // Redraw after seek
    }

    // Start the drawing loop
    drawCaptions();

    return () => {
      window.removeEventListener('timeline-seek', handleTimelineSeek);
      if (videoElement) {
        videoElement.removeEventListener('timeupdate', handleTimeUpdate);
        videoElement.removeEventListener('loadedmetadata', handleMetadata);
        videoElement.removeEventListener('play', () => videoState.setPlaying(false)); // Fix: Set to false on pause
        videoElement.removeEventListener('pause', () => videoState.setPlaying(false));
        videoElement.removeEventListener('seeked', drawCaptions);
      }
      cancelAnimationFrame(animationFrame);
    };
  });

  // Ensure canvas dimensions update if project resolution changes
  afterUpdate(() => {
    if (canvasElement && (canvasElement.width !== videoWidth || canvasElement.height !== videoHeight)) {
      canvasElement.width = videoWidth;
      canvasElement.height = videoHeight;
      drawCaptions(); // Redraw after resizing
    }
  });

  function handleTimelineSeek(event) {
    if (videoElement && event.detail && typeof event.detail.time === 'number') {
      videoElement.currentTime = event.detail.time;
      drawCaptions(); // Redraw immediately after seek
    }
  }

  function handleTimeUpdate() {
    if (videoElement) {
      videoState.setCurrentTime(videoElement.currentTime);
      drawCaptions(); // Redraw on time update
    }
  }

  function handleMetadata() {
    if (videoElement) {
      videoState.update(v => ({ ...v, duration: videoElement.duration }));
      if (project?.resolution) { // Update video dimensions from project if available
        [videoWidth, videoHeight] = project.resolution.split('x').map(Number);
      } else { // Fallback to video element dimensions if no project resolution
        videoWidth = videoElement.videoWidth;
        videoHeight = videoElement.videoHeight;
      }
      canvasElement.width = videoWidth;
      canvasElement.height = videoHeight;
      drawCaptions(); // Redraw after metadata load
    }
  }

  function togglePlay() {
    if (videoElement) {
      if (videoElement.paused) {
        videoElement.play();
      } else {
        videoElement.pause();
      }
    }
  }

  function drawCaptions() {
    if (!ctx || !project || !video) {
      animationFrame = requestAnimationFrame(drawCaptions);
      return;
    }

    ctx.clearRect(0, 0, canvasElement.width, canvasElement.height); // Clear canvas

    const currentTime = video.currentTime;
    const captions = project.captions || [];
    const style = project.style || {};

    // Find the active caption (segment)
    const activeCaption = captions.find(c => 
      currentTime >= c.start && currentTime <= c.end
    );

    if (activeCaption) {
      // Calculate caption position
      let yPos;
      const textHeight = parseInt(style.fontSize || 42, 10);
      const lineHeight = textHeight * (style.lineHeight || 1.2);
      const margin = 50; // Bottom margin

      switch (style.position) {
        case 'top': yPos = margin + textHeight; break;
        case 'middle': yPos = canvasElement.height / 2; break; // Use canvasElement.height
        case 'bottom':
        default: yPos = canvasElement.height - margin; break; // Use canvasElement.height
      }

      // Load font dynamically to ensure it's available for canvas
      // This is a simplified approach; for production, consider a font loading library
      document.fonts.load(`${style.fontWeight || 'bold'} ${textHeight}px "${style.fontFamily || 'Inter'}"`)
        .then(() => {
          ctx.font = `${style.fontWeight || 'bold'} ${textHeight}px "${style.fontFamily || 'Inter'}", sans-serif`;
          ctx.fillStyle = style.color || '#FFFFFF';
          ctx.textAlign = style.alignment || 'center';

          // Apply text shadow if any
          const textShadowCSS = getTextShadowCSSForCanvas(style.textShadow || 'medium');
          if (textShadowCSS) {
            const parts = textShadowCSS.match(/(\d+)px (\d+)px (\d+)px (.*)/);
            if (parts) {
              ctx.shadowOffsetX = parseInt(parts[1], 10);
              ctx.shadowOffsetY = parseInt(parts[2], 10);
              ctx.shadowBlur = parseInt(parts[3], 10);
              ctx.shadowColor = parts[4];
            }
          } else {
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            ctx.shadowBlur = 0;
            ctx.shadowColor = 'transparent';
          }

          // Check if word-by-word animation is enabled
          if (style.wordByWord && activeCaption.words && activeCaption.words.length > 0) {
            const wordsInLine = [];
            let lineAccumulatedWidth = 0;
            const spacing = ctx.measureText(' ').width; // Space between words
            const maxLineWidth = canvasElement.width - 2 * margin; // Max width for a line

            let currentY = yPos; // Starting Y position

            for (const wordObj of activeCaption.words) {
              const wordWidth = ctx.measureText(wordObj.text).width;
              
              if (lineAccumulatedWidth + wordWidth + spacing > maxLineWidth && wordsInLine.length > 0) {
                // Draw current line
                drawWordLine(wordsInLine, currentY, lineAccumulatedWidth - spacing); // Adjust for last spacing
                wordsInLine.length = 0;
                lineAccumulatedWidth = 0;
                currentY += lineHeight; // Move to next line
              }
              wordsInLine.push(wordObj);
              lineAccumulatedWidth += wordWidth + spacing;
            }
            if (wordsInLine.length > 0) {
              drawWordLine(wordsInLine, currentY, lineAccumulatedWidth - spacing);
            }

          } else {
            // Render full caption text
            ctx.fillText(activeCaption.text, canvasElement.width / 2, yPos);
          }
        });
    }

    animationFrame = requestAnimationFrame(drawCaptions);
  }

  function drawWordLine(wordsInLine, yPos, lineActualWidth) {
      let startX = (canvasElement.width / 2) - lineActualWidth / 2; // Center the line

      for (const wordObj of wordsInLine) {
        const isActiveWord = video.currentTime >= wordObj.start && video.currentTime <= wordObj.end;
        const wordWidth = ctx.measureText(wordObj.text).width;
        const spacing = ctx.measureText(' ').width;
        
        ctx.save(); // Save current canvas state

        // Apply animation
        if (isActiveWord) {
            const progress = (video.currentTime - wordObj.start) / (wordObj.end - wordObj.start); // 0 to 1
            const animationType = project.style.animation;

            switch (animationType) {
                case 'pop':
                    const scaleFactor = 1 + Math.sin(progress * Math.PI) * 0.2; // Pop animation (0 to PI)
                    ctx.translate(startX + wordWidth / 2, yPos);
                    ctx.scale(scaleFactor, scaleFactor);
                    ctx.translate(-(startX + wordWidth / 2), -yPos);
                    break;
                case 'slide-up':
                    const translateY = Math.max(0, 1 - progress) * 20; // Slide up 20px
                    ctx.translate(0, -translateY);
                    break;
                case 'fade':
                    ctx.globalAlpha = progress; // Fade in
                    break;
                case 'bounce':
                    // Simple bounce: scale up then down
                    let bounceScale = 1;
                    if (progress < 0.5) {
                        bounceScale = 1 + progress * 0.4; // Scale up to 1.2
                    } else {
                        bounceScale = 1 + (1 - progress) * 0.4; // Scale down
                    }
                    ctx.translate(startX + wordWidth / 2, yPos);
                    ctx.scale(bounceScale, bounceScale);
                    ctx.translate(-(startX + wordWidth / 2), -yPos);
                    break;
                case 'none':
                default:
                    // No animation
                    break;
            }
        }

        let originalFont = ctx.font; // Store original font to restore later
        let currentFillStyle = project.style.color || '#FFFFFF';
        let currentBgFillStyle = 'transparent'; // For keyword background
        let isDrawingHighlightBackground = false;

        if (isActiveWord && project.style.highlightWords) {
          currentFillStyle = project.style.highlightColor || '#FFD700';
          currentBgFillStyle = project.style.highlightColor || '#FFD700'; // For active word background
          isDrawingHighlightBackground = true;
          // Adjust text color for contrast if highlight background is same as text
          if (project.style.color === project.style.highlightColor) {
            currentFillStyle = '#000000'; // Black text on color background
          }
        } else if (wordObj.isKeyword) {
          // Keyword highlighting (persistent)
          currentFillStyle = project.style.keywordColor || '#EC4899'; // Use secondary color
          const textHeight = parseInt(project.style.fontSize || 42, 10);
          ctx.font = `bold ${textHeight}px "${project.style.fontFamily || 'Inter'}", sans-serif`; // Apply bold font weight for keywords
        }

        // Draw word background (highlight effect for active words, or optionally for keywords)
        if (isDrawingHighlightBackground) {
          const textMetrics = ctx.measureText(wordObj.text);
          const bgPaddingX = 10;
          const bgPaddingY = 8;
          ctx.fillStyle = currentBgFillStyle;
          ctx.fillRect(
            startX - bgPaddingX / 2,
            yPos - textMetrics.actualBoundingBoxAscent - bgPaddingY / 2,
            textMetrics.width + bgPaddingX,
            textMetrics.actualBoundingBoxAscent + textMetrics.actualBoundingBoxDescent + bgPaddingY
          );
        }
        
        ctx.fillStyle = currentFillStyle; // Apply determined fill style
        ctx.fillText(wordObj.text, startX, yPos); // Draw the word text

        if (wordObj.isKeyword) {
            ctx.font = originalFont; // Restore original font after drawing keyword
        }
  }

  // Helper to convert Tailwind-like text-shadow to Canvas properties
  function getTextShadowCSSForCanvas(shadowStyle) {
    switch (shadowStyle) {
      case 'light': return '1px 1px 2px rgba(0,0,0,0.5)';
      case 'medium': return '2px 2px 4px rgba(0,0,0,0.7)';
      case 'heavy': return '3px 3px 6px rgba(0,0,0,0.9)';
      default: return '';
    }
  }

</script>

<div 
  class="relative w-full max-w-md aspect-[9/16] bg-black rounded-2xl overflow-hidden shadow-2xl"
>
  <!-- Video Element -->
  <video
    bind:this={videoElement}
    src={project?.videoUrl}
    class="w-full h-full object-contain"
    on:click={togglePlay}
    crossorigin="anonymous"
    playsinline
    muted
  >
    <track kind="captions" />
  </video>

  <!-- Canvas for dynamic captions -->
  <canvas 
    bind:this={canvasElement}
    class="absolute top-0 left-0 w-full h-full pointer-events-none"
  ></canvas>

  <!-- Play Button Overlay (when paused) -->
  {#if !video.isPlaying}
    <button 
      class="absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity hover:bg-black/40"
      on:click={togglePlay}
    >
      <div class="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center shadow-lg">
        <svg class="w-8 h-8 text-dark ml-1" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </div>
    </button>
  {/if}

  <!-- Current Time Indicator -->
  <div class="absolute bottom-4 left-4 text-white text-sm font-mono bg-black/60 px-2 py-1 rounded">
    {Math.floor(video.currentTime / 60)}:{(Math.floor(video.currentTime) % 60).toString().padStart(2, '0')}
  </div>
</div>

