<script>
  import { currentProject } from '../stores/projectStore';
  import { videoState } from '../stores/videoPlayerStore';
  import { uiState } from '../stores/uiStore';
  import { Film } from 'lucide-svelte';
  import { formatTime } from '../utils';

  let timelineRef;

  $: duration = $currentProject?.videoDuration || 1;
  $: captions = $currentProject?.captions || [];
  $: currentTime = $videoState.currentTime;

  function handleTimelineClick(e) {
    if (!timelineRef || duration <= 0) return;
    
    const rect = timelineRef.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const percentage = Math.max(0, Math.min(1, y / rect.height));
    const time = percentage * duration;
    
    videoState.setCurrentTime(time);
    window.dispatchEvent(new CustomEvent('timeline-seek', { detail: { time } }));
  }

  function handleCaptionClick(caption) {
    uiState.update(u => ({ ...u, selectedCaptionId: caption.id }));
    videoState.setCurrentTime(caption.start);
    window.dispatchEvent(new CustomEvent('timeline-seek', { detail: { time: caption.start } }));
  }

  function getCaptionStyle(caption) {
    const top = (caption.start / duration) * 100;
    const height = ((caption.end - caption.start) / duration) * 100;
    return `top: ${top}%; height: ${Math.max(1, height)}%;`;
  }

  function getPlayheadStyle() {
    if (!duration || duration <= 0) return 'top: 0%;';
    const top = (currentTime / duration) * 100;
    return `top: ${Math.max(0, Math.min(100, top))}%;`;
  }
</script>

<div class="h-full flex flex-col bg-dark">
  <!-- Timeline Header -->
  <div class="h-10 border-b border-dark-lighter flex items-center justify-center px-2 bg-dark-light">
    <span class="text-xs font-medium text-dark-text-light transform -rotate-90 whitespace-nowrap">Timeline</span>
  </div>

  <!-- Vertical Timeline Track -->
  <div class="flex-1 relative overflow-y-auto overflow-x-hidden">
    <button
      bind:this={timelineRef}
      class="absolute inset-0 w-full cursor-pointer bg-transparent border-none p-0"
      on:click={handleTimelineClick}
      aria-label="Timeline scrubber"
    >
      <!-- Time Grid - Horizontal lines -->
      <div class="absolute inset-0 pointer-events-none">
        {#each Array(Math.max(1, Math.ceil(duration / 10))) as _, i}
          <div 
            class="absolute left-0 right-0 border-t border-dark-lighter"
            style="top: {(i * 10 / duration) * 100}%"
          />
        {/each}
      </div>

      <!-- Caption Blocks - Vertical layout -->
      <div class="absolute top-0 bottom-0 left-2 right-2">
        {#each captions as caption}
          <button
            class="absolute left-0 right-0 rounded bg-primary-dark border-2 border-primary-dark hover:bg-primary transition flex flex-col items-center justify-center px-1 overflow-hidden text-xs text-white {$uiState.selectedCaptionId === caption.id ? 'ring-2 ring-primary' : ''}"
            style={getCaptionStyle(caption)}
            on:click|stopPropagation={() => handleCaptionClick(caption)}
            title={caption.text}
          >
            <span class="truncate w-full text-center leading-tight" style="font-size: 8px;">
              {caption.text.slice(0, 20)}{caption.text.length > 20 ? '...' : ''}
            </span>
          </button>
        {/each}
      </div>

      <!-- B-Roll Track -->
      {#if $currentProject?.bRollClips?.length > 0}
        <div class="absolute top-0 bottom-0 left-1 right-1">
          {#each $currentProject.bRollClips as clip}
            <div
              class="absolute left-0 right-0 rounded bg-secondary border-2 border-secondary flex items-center justify-center overflow-hidden"
              style="top: {(clip.start / duration) * 100}%; height: {(clip.duration / duration) * 100}%;"
            >
              <Film class="w-3 h-3 text-white" />
            </div>
          {/each}
        </div>
      {/if}

      <!-- Horizontal Playhead -->
      <div 
        class="absolute left-0 right-0 h-0.5 bg-red-500 z-10 pointer-events-none transition-all duration-75 ease-linear"
        style={getPlayheadStyle()}
      >
        <div class="absolute -left-1.5 -top-1 w-3 h-3 bg-red-500 rounded-full" />
      </div>
    </button>
  </div>

  <!-- Time Display -->
  <div class="h-10 border-t border-dark-lighter flex items-center justify-center bg-dark-light">
    <span class="text-xs font-mono text-dark-text-light transform -rotate-90 whitespace-nowrap">
      {formatTime(currentTime)}
    </span>
  </div>
</div>
