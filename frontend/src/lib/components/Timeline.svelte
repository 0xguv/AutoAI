<script>
  import { currentProject, videoState, uiState } from '../stores/editor';
  import { Film } from 'lucide-svelte';
  import { formatTime } from '../utils';

  let timelineRef;
  let isDragging = false;

  $: duration = $currentProject?.videoDuration || 1; // Prevent division by zero
  $: captions = $currentProject?.captions || [];
  $: currentTime = $videoState.currentTime;
  $: zoom = 50;

  function handleTimelineClick(e) {
    if (!timelineRef || duration <= 0) return;
    
    const rect = timelineRef.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const time = percentage * duration;
    
    videoState.setCurrentTime(time);
    
    // Dispatch custom event for VideoPreview to seek
    window.dispatchEvent(new CustomEvent('timeline-seek', { detail: { time } }));
  }

  function handleCaptionClick(caption) {
    uiState.update(u => ({ ...u, selectedCaptionId: caption.id }));
    videoState.setCurrentTime(caption.start);
    window.dispatchEvent(new CustomEvent('timeline-seek', { detail: { time: caption.start } }));
  }

  function getCaptionStyle(caption) {
    const left = (caption.start / duration) * 100;
    const width = ((caption.end - caption.start) / duration) * 100;
    return `left: ${left}%; width: ${Math.max(0.5, width)}%;`;
  }

  function getPlayheadStyle() {
    if (!duration || duration <= 0) return 'left: 0%;';
    const left = (currentTime / duration) * 100;
    return `left: ${Math.max(0, Math.min(100, left))}%;`;
  }
</script>

<div class="h-full flex flex-col bg-white">
  <!-- Timeline Header -->
  <div class="h-8 border-b border-gray-200 flex items-center px-4 text-xs text-gray-500">
    <span class="w-20 font-medium">Timeline</span>
    <div class="flex-1 flex justify-between">
      {#each Array(6) as _, i}
        <span>{formatTime((duration / 5) * i)}</span>
      {/each}
    </div>
  </div>

  <!-- Timeline Tracks -->
  <div class="flex-1 relative overflow-x-auto overflow-y-hidden">
    <button
      bind:this={timelineRef}
      class="absolute inset-0 min-w-full cursor-pointer bg-transparent border-none p-0"
      on:click={handleTimelineClick}
      aria-label="Timeline scrubber"
    >
      <!-- Time Grid -->
      <div class="absolute inset-0 pointer-events-none">
        {#each Array(Math.max(1, Math.ceil(duration / 5))) as _, i}
          <div 
            class="absolute top-0 bottom-0 border-l border-gray-200"
            style="left: {(i * 5 / duration) * 100}%"
          />
        {/each}
      </div>

      <!-- Caption Track -->
      <div class="absolute top-4 left-0 right-0 h-16 px-2">
        {#each captions as caption}
          <button
            class="absolute h-12 rounded bg-blue-100 border-2 border-blue-300 hover:bg-blue-200 transition flex items-center px-2 overflow-hidden text-xs text-left text-blue-900 {$uiState.selectedCaptionId === caption.id ? 'ring-2 ring-blue-500' : ''}"
            style={getCaptionStyle(caption)}
            on:click|stopPropagation={() => handleCaptionClick(caption)}
          >
            <span class="truncate">{caption.text}</span>
          </button>
        {/each}
      </div>

      <!-- B-Roll Track -->
      {#if $currentProject?.bRollClips?.length > 0}
        <div class="absolute top-24 left-0 right-0 h-12 px-2">
          {#each $currentProject.bRollClips as clip}
            <div
              class="absolute h-10 rounded bg-purple-100 border-2 border-purple-300 flex items-center px-2 overflow-hidden text-xs text-purple-900"
              style="left: {(clip.start / duration) * 100}%; width: {(clip.duration / duration) * 100}%;"
            >
              <Film class="w-3 h-3 mr-1" />
              <span class="truncate">B-Roll</span>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Playhead -->
      <div 
        class="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10 pointer-events-none transition-all duration-75 ease-linear"
        style={getPlayheadStyle()}
      >
        <div class="absolute -top-1 -left-1.5 w-3 h-3 bg-red-500 rounded-full" />
      </div>
    </button>
  </div>

  <!-- Zoom Controls -->
  <div class="h-10 border-t border-gray-200 flex items-center px-4 gap-4 bg-gray-50">
    <button 
      class="text-gray-500 hover:text-gray-900 transition"
      on:click={() => zoom = Math.max(20, zoom - 10)}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
      </svg>
    </button>
    <span class="text-xs text-gray-500">Zoom</span>
    <button 
      class="text-gray-500 hover:text-gray-900 transition"
      on:click={() => zoom = Math.min(200, zoom + 10)}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
      </svg>
    </button>
  </div>
</div>
