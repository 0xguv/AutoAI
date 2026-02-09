<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentProject, videoState, activeCaption, activeWord } from '../stores/editor';
  import { getTextShadowCSS, getAnimationCSS } from '../utils';

  let videoElement;
  let containerRef;
  let animationFrame;

  $: style = $currentProject?.style || {};
  $: caption = $activeCaption;
  $: word = $activeWord;
  $: words = caption?.words || [];
  $: currentTime = $videoState.currentTime;

  onMount(() => {
    // Listen for timeline seek events
    window.addEventListener('timeline-seek', handleTimelineSeek);
    
    if (videoElement) {
      videoElement.addEventListener('timeupdate', handleTimeUpdate);
      videoElement.addEventListener('loadedmetadata', handleMetadata);
      videoElement.addEventListener('play', () => videoState.setPlaying(true));
      videoElement.addEventListener('pause', () => videoState.setPlaying(false));
    }

    return () => {
      window.removeEventListener('timeline-seek', handleTimelineSeek);
      if (videoElement) {
        videoElement.removeEventListener('timeupdate', handleTimeUpdate);
        videoElement.removeEventListener('loadedmetadata', handleMetadata);
      }
      cancelAnimationFrame(animationFrame);
    };
  });

  function handleTimelineSeek(event) {
    if (videoElement && event.detail && typeof event.detail.time === 'number') {
      videoElement.currentTime = event.detail.time;
    }
  }

  function handleTimeUpdate() {
    if (videoElement) {
      videoState.setCurrentTime(videoElement.currentTime);
    }
  }

  function handleMetadata() {
    if (videoElement) {
      videoState.update(v => ({ ...v, duration: videoElement.duration }));
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

  function getCaptionStyles() {
    return {
      fontFamily: style.fontFamily || 'Inter',
      fontSize: `${style.fontSize || 42}px`,
      fontWeight: style.fontWeight || 'bold',
      color: style.color || '#FFFFFF',
      textShadow: getTextShadowCSS(style.textShadow || 'medium'),
      textTransform: style.textTransform || 'none',
      letterSpacing: `${style.letterSpacing || 0}px`,
      lineHeight: style.lineHeight || 1.2,
      textAlign: style.alignment || 'center'
    };
  }

  function getWordStyles(wordObj) {
    const isActive = wordObj === word;
    return {
      backgroundColor: isActive && style.highlightWords ? style.highlightColor || '#FFD700' : 'transparent',
      color: isActive && style.highlightWords ? '#000000' : style.color || '#FFFFFF',
      padding: isActive && style.highlightWords ? '2px 6px' : '0',
      borderRadius: isActive && style.highlightWords ? '4px' : '0',
      transition: 'all 0.1s ease'
    };
  }

  function getPositionClasses() {
    switch (style.position) {
      case 'top': return 'top-16';
      case 'middle': return 'top-1/2 -translate-y-1/2';
      case 'bottom':
      default: return 'bottom-24';
    }
  }

  $: animationClass = getAnimationCSS(style.animation || 'pop');
</script>

<div 
  bind:this={containerRef}
  class="relative w-full max-w-md aspect-[9/16] bg-black rounded-2xl overflow-hidden shadow-2xl"
>
  <!-- Video Element -->
  <video
    bind:this={videoElement}
    src={$currentProject?.videoUrl}
    class="w-full h-full object-contain"
    on:click={togglePlay}
    crossorigin="anonymous"
    playsinline
  >
    <track kind="captions" />
  </video>

  <!-- Caption Overlay -->
  {#if caption}
    <div 
      class="absolute inset-x-6 {getPositionClasses()} {animationClass}"
      style={getCaptionStyles()}
    >
      {#if style.wordByWord && words.length > 0}
        <span class="inline-flex flex-wrap justify-center gap-1">
          {#each words as wordObj}
            <span style={getWordStyles(wordObj)}>
              {wordObj.text}
            </span>
          {/each}
        </span>
      {:else}
        {caption.text}
      {/if}
    </div>
  {/if}

  <!-- Play Button Overlay (when paused) -->
  {#if !$videoState.isPlaying}
    <button 
      class="absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity hover:bg-black/40"
      on:click={togglePlay}
    >
      <div class="w-16 h-16 rounded-full bg-white/90 flex items-center justify-center shadow-lg">
        <svg class="w-8 h-8 text-gray-900 ml-1" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </div>
    </button>
  {/if}

  <!-- Current Time Indicator -->
  <div class="absolute bottom-4 left-4 text-white text-sm font-mono bg-black/60 px-2 py-1 rounded">
    {Math.floor(currentTime / 60)}:{(Math.floor(currentTime) % 60).toString().padStart(2, '0')}
  </div>
</div>
