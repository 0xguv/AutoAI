<script>
  import { currentProject, videoState, uiState } from '../stores/editor';
  import { formatTime } from '../utils';

  let timelineRef;
  let isDragging = false;
  let dragType = null;
  let draggedCaptionId = null;

  $: duration = $currentProject?.videoDuration || 0;
  $: captions = $currentProject?.captions || [];
  $: currentTime = $videoState.currentTime;
  $: zoom = 50; // pixels per second

  function handleTimelineClick(e) {
    const rect = timelineRef.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = (x / rect.width) * duration;
    videoState.setCurrentTime(Math.max(0, Math.min(time, duration)));
  }

  function handleCaptionClick(caption) {
    uiState.update(u => ({ ...u, selectedCaptionId: caption.id }));
    videoState.setCurrentTime(caption.start);
  }

  function getCaptionStyle(caption) {
    const left = (caption.start / duration) * 100;
    const width = ((caption.end - caption.start) / duration) * 100;
    const isSelected = $uiState.selectedCaptionId === caption.id;
    
    return `left: ${left}%; width: ${width}%;`;
  }

  function getPlayheadStyle() {
    const left = (currentTime / duration) * 100;
    return `left: ${left}%;`;
  }
</script>

<div class="h-full flex flex-col bg-[#0f0f0f]">
  <!-- Timeline Header -->
  <div class="h-8 border-b border-white/10 flex items-center px-4 text-xs text-gray-500">
    <span class="w-20">Timeline</span>
    <div class="flex-1 flex justify-between">
      {#each Array(6) as _, i}
        <span>{formatTime((duration / 5) * i)}</span>
      {/each}
    </div>
  </div>

  <!-- Timeline Tracks -->
  <div class="flex-1 relative overflow-x-auto overflow-y-hidden">
    <div 
      bind:this={timelineRef}
      class="absolute inset-0 min-w-full"
      on:click={handleTimelineClick}
    >
      <!-- Time Grid -->
      <div class="absolute inset-0 pointer-events-none">
        {#each Array(Math.ceil(duration / 5)) as _, i}
          <div 
            class="absolute top-0 bottom-0 border-l border-white/5"
            style="left: {(i * 5 / duration) * 100}%"
          />
        {/each}
      </div>

      <!-- Caption Track -->
      <div class="absolute top-4 left-0 right-0 h-16 px-2">
        {#each captions as caption}
          <button
            class="absolute h-12 rounded bg-blue-500/30 border-2 border-blue-500/50 hover:bg-blue-500/50 transition flex items-center px-2 overflow-hidden text-xs text-left {$uiState.selectedCaptionId === caption.id ? 'ring-2 ring-white' : ''}"
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
              class="absolute h-10 rounded bg-purple-500/30 border-2 border-purple-500/50 flex items-center px-2 overflow-hidden text-xs"
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
        class="absolute top-0 bottom-0 w-px bg-red-500 z-10 pointer-events-none"
        style={getPlayheadStyle()}
      >
        <div class="absolute -top-1 -left-1.5 w-3 h-3 bg-red-500 rounded-full" />
      </div>
    </div>
  </div>

  <!-- Zoom Controls -->
  <div class="h-10 border-t border-white/10 flex items-center px-4 gap-4">
    <button 
      class="text-gray-400 hover:text-white transition"
      on:click={() => zoom = Math.max(20, zoom - 10)}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
      </svg>
    </button>
    <span class="text-xs text-gray-500">Zoom</span>
    <button 
      class="text-gray-400 hover:text-white transition"
      on:click={() => zoom = Math.min(200, zoom + 10)}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
      </svg>
    </button>
  </div>
</div>

<script context="module">
  import { Film } from 'lucide-svelte';
</script>
