<script>
  import { onMount, onDestroy } from 'svelte';
  import { currentProject } from '../stores/projectStore';
  import { videoState } from '../stores/videoPlayerStore';

  let videoElement;
  
  $: project = $currentProject;
  $: video = $videoState;
  
  // Get active caption for current time
  $: activeCaption = project?.captions?.find(c => 
    video?.currentTime >= c.start && video?.currentTime <= c.end
  );
  
  // Get active words for word-by-word highlighting
  $: activeWords = activeCaption?.words?.filter(w => 
    video?.currentTime >= w.start && video?.currentTime <= w.end
  ) || [];

  function handlePlay() { 
    videoState.setPlaying(true); 
  }
  
  function handlePause() { 
    videoState.setPlaying(false); 
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
  
  function handleTimelineSeek(event) {
    if (videoElement && event.detail?.time != null) {
      videoElement.currentTime = event.detail.time;
    }
  }

  onMount(() => {
    window.addEventListener('timeline-seek', handleTimelineSeek);
    
    if (videoElement) {
      videoElement.addEventListener('timeupdate', handleTimeUpdate);
      videoElement.addEventListener('loadedmetadata', handleMetadata);
      videoElement.addEventListener('play', handlePlay);
      videoElement.addEventListener('pause', handlePause);
    }

    return () => {
      window.removeEventListener('timeline-seek', handleTimelineSeek);
      if (videoElement) {
        videoElement.removeEventListener('timeupdate', handleTimeUpdate);
        videoElement.removeEventListener('loadedmetadata', handleMetadata);
        videoElement.removeEventListener('play', handlePlay);
        videoElement.removeEventListener('pause', handlePause);
      }
    };
  });

  function togglePlay() {
    if (videoElement) {
      if (videoElement.paused) {
        videoElement.play();
      } else {
        videoElement.pause();
      }
    }
  }
  
  // Get caption position styles
  function getCaptionPosition() {
    const position = project?.style?.position || 'bottom';
    switch (position) {
      case 'top': return 'top: 10%;';
      case 'middle': return 'top: 50%; transform: translateY(-50%);';
      case 'bottom':
      default: return 'bottom: 10%;';
    }
  }
  
  // Check if a word is currently active
  function isWordActive(word) {
    return video?.currentTime >= word.start && video?.currentTime <= word.end;
  }
  
  // Get word animation class
  function getWordAnimationClass(word) {
    if (!isWordActive(word)) return '';
    const animation = project?.style?.animation || 'none';
    switch (animation) {
      case 'pop': return 'animate-pop';
      case 'slide-up': return 'animate-slide-up';
      case 'fade': return 'animate-fade';
      case 'bounce': return 'animate-bounce';
      default: return '';
    }
  }
</script>

<div 
  class="relative w-full max-w-md aspect-[9/16] bg-black rounded-2xl overflow-hidden shadow-2xl"
>
  <!-- Video Element - SIMPLIFIED -->
  {#if project?.videoUrl}
    <video
      bind:this={videoElement}
      src={project.videoUrl}
      class="w-full h-full object-contain"
      on:click={togglePlay}
      crossorigin="anonymous"
      playsinline
      muted
      autoplay
    >
      <track kind="captions" />
    </video>
  {:else}
    <div class="w-full h-full flex items-center justify-center bg-black">
      <div class="text-center">
        <svg class="w-16 h-16 text-gray-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-white text-lg">No video loaded</p>
      </div>
    </div>
  {/if}

  <!-- HTML Caption Overlay - REPLACES CANVAS -->
  {#if activeCaption}
    <div 
      class="absolute left-4 right-4 text-center pointer-events-none"
      style="{getCaptionPosition()} {project?.style?.textShadow === 'heavy' ? 'text-shadow: 3px 3px 6px rgba(0,0,0,0.9);' : project?.style?.textShadow === 'light' ? 'text-shadow: 1px 1px 2px rgba(0,0,0,0.5);' : 'text-shadow: 2px 2px 4px rgba(0,0,0,0.7);'}"
    >
      {#if project?.style?.wordByWord && activeCaption.words}
        <!-- Word-by-word display -->
        <div class="flex flex-wrap justify-center gap-1">
          {#each activeCaption.words as word}
            <span 
              class="inline-block px-1 py-0.5 rounded transition-all duration-150 {getWordAnimationClass(word)}"
              style="
                font-family: {project?.style?.fontFamily || 'Inter'}, sans-serif;
                font-size: {project?.style?.fontSize || 42}px;
                font-weight: {project?.style?.fontWeight || 'bold'};
                color: {isWordActive(word) && project?.style?.highlightWords ? (project?.style?.highlightColor || '#FFD700') : (project?.style?.color || '#FFFFFF')};
                background-color: {isWordActive(word) && project?.style?.highlightWords ? (project?.style?.highlightColor || '#FFD700') : 'transparent'};
                {isWordActive(word) && project?.style?.highlightWords && project?.style?.color === project?.style?.highlightColor ? 'color: #000000;' : ''}
              "
            >
              {word.text}
            </span>
          {/each}
        </div>
      {:else}
        <!-- Full caption text -->
        <p 
          class="leading-tight"
          style="
            font-family: {project?.style?.fontFamily || 'Inter'}, sans-serif;
            font-size: {project?.style?.fontSize || 42}px;
            font-weight: {project?.style?.fontWeight || 'bold'};
            color: {project?.style?.color || '#FFFFFF'};
          "
        >
          {activeCaption.text}
        </p>
      {/if}
    </div>
  {/if}

  <!-- Play Button Overlay (when paused) -->
  {#if !video.isPlaying}
    <button 
      class="absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity hover:bg-black/40 z-10"
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
  <div class="absolute bottom-4 left-4 text-white text-sm font-mono bg-black/60 px-2 py-1 rounded z-10">
    {Math.floor(video.currentTime / 60)}:{(Math.floor(video.currentTime) % 60).toString().padStart(2, '0')}
  </div>
</div>

<style>
  @keyframes pop {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.2); }
  }
  
  @keyframes slide-up {
    0% { transform: translateY(20px); opacity: 0; }
    100% { transform: translateY(0); opacity: 1; }
  }
  
  @keyframes fade-in {
    0% { opacity: 0; }
    100% { opacity: 1; }
  }
  
  .animate-pop {
    animation: pop 0.3s ease-out;
  }
  
  .animate-slide-up {
    animation: slide-up 0.3s ease-out;
  }
  
  .animate-fade {
    animation: fade-in 0.3s ease-out;
  }
</style>

