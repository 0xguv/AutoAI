<script>
  import { currentProject } from '../stores/projectStore';
  import { videoState } from '../stores/videoPlayerStore';
  import { uiState } from '../stores/uiStore';
  import { Film, Trash2 } from 'lucide-svelte'; // Import Trash2 icon
  import { formatTime } from '../utils';
  import { onMount, onDestroy } from 'svelte'; // Import onMount, onDestroy

  let timelineRef;

  // Dragging state
  let isDraggingClip = false;
  let draggedClipId = null;
  let dragStartY = 0; // Mouse Y position when drag starts
  let initialClipStart = 0; // Clip's start time when drag starts
  let timelineRect; // Store timeline's bounding rect

  $: duration = $currentProject?.videoDuration || 1;
  $: captions = $currentProject?.captions || [];
  $: bRollClips = $currentProject?.bRollClips || []; // Reactive for bRollClips
  $: zoomEffects = $currentProject?.zoomEffects || []; // New: Reactive for zoom effects
  $: soundEffects = $currentProject?.soundEffects || []; // New: Reactive for sound effects
  $: currentTime = $videoState.currentTime;

  onMount(() => {
    // Cache timelineRef rect for calculations
    timelineRect = timelineRef.getBoundingClientRect();

    window.addEventListener('mousemove', handleDragMove);
    window.addEventListener('mouseup', handleDragEnd);

    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
    };
  });

  // Function to start dragging
  function handleDragStart(e, clipId, currentStart) {
    if (e.button !== 0) return; // Only left click
    isDraggingClip = true;
    draggedClipId = clipId;
    dragStartY = e.clientY;
    initialClipStart = currentStart;
    timelineRect = timelineRef.getBoundingClientRect(); // Recalculate in case of scroll/resize
    e.preventDefault(); // Prevent text selection etc.
  }

  // Function to handle dragging movement
  function handleDragMove(e) {
    if (!isDraggingClip || !draggedClipId || !timelineRef) return;

    const dragDeltaY = e.clientY - dragStartY; // Pixel change
    const percentageChange = dragDeltaY / timelineRect.height;
    const timeChange = percentageChange * duration;

    let newStart = initialClipStart + timeChange;
    
    // Clamp start time to video duration
    newStart = Math.max(0, Math.min(newStart, duration - ($currentProject.bRollClips.find(c => c.id === draggedClipId)?.duration || 0)));

    currentProject.updateBRollClipStart(draggedClipId, newStart);
  }

  // Function to end dragging
  function handleDragEnd() {
    isDraggingClip = false;
    draggedClipId = null;
  }

  function handleTimelineClick(e) {
    if (!timelineRef || duration <= 0) return;
    
    // Only seek if not dragging
    if (isDraggingClip) return;

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

  // New function to remove B-roll clip
  function removeBRoll(clipId) {
    currentProject.removeBRoll(clipId);
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
    <span class="text-xs font-medium text-dark-text-light">Timeline</span>
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
            class="absolute left-0 right-0 mx-1 rounded bg-primary-dark border-2 border-primary-dark hover:bg-primary transition flex flex-col items-center justify-center px-2 overflow-hidden text-white {$uiState.selectedCaptionId === caption.id ? 'ring-2 ring-primary' : ''}"
            style={getCaptionStyle(caption)}
            on:click|stopPropagation={() => handleCaptionClick(caption)}
            title={caption.text}
          >
            <span class="truncate w-full text-center leading-tight text-xs">
              {caption.text.slice(0, 30)}{caption.text.length > 30 ? '...' : ''}
            </span>
          </button>
        {/each}
      </div>

      <!-- B-Roll Track -->
      {#if bRollClips.length > 0}
        <div class="absolute top-0 bottom-0 left-1 right-1">
          {#each bRollClips as clip (clip.id)}
            <div
              class="absolute left-0 right-0 rounded bg-secondary-dark border-2 border-secondary hover:border-primary transition flex items-center justify-center overflow-hidden cursor-grab active:cursor-grabbing group"
              style="top: {(clip.start / duration) * 100}%; height: {(clip.duration / duration) * 100}%;"
              on:mousedown={(e) => handleDragStart(e, clip.id, clip.start)}
              title="Drag to move B-Roll: {clip.keyword || 'clip'}"
            >
              <Film class="w-3 h-3 text-white" />
              <button 
                class="absolute top-1 right-1 p-0.5 bg-black/50 hover:bg-black rounded-full text-white opacity-0 group-hover:opacity-100 transition-opacity"
                on:click|stopPropagation={() => removeBRoll(clip.id)}
                title="Remove B-Roll Clip"
              >
                <Trash2 class="w-3 h-3" />
              </button>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Zoom Effects Track -->
      {#if zoomEffects.length > 0}
        <div class="absolute top-0 bottom-0 left-3 right-3 opacity-70">
          {#each zoomEffects as effect (effect.id)}
            <div
              class="absolute left-0 right-0 rounded-sm bg-purple-500/50 border border-purple-400"
              style="top: {(effect.start / duration) * 100}%; height: {((effect.end - effect.start) / duration) * 100}%;"
              title="Zoom: {effect.type} at {formatTime(effect.start)}"
            >
            </div>
          {/each}
        </div>
      {/if}

      <!-- Sound Effects Track -->
      {#if soundEffects.length > 0}
        <div class="absolute top-0 bottom-0 left-5 right-5 opacity-70">
          {#each soundEffects as effect (effect.id)}
            <div
              class="absolute left-0 right-0 rounded-full bg-blue-500/50 border border-blue-400 h-2"
              style="top: {(effect.start / duration) * 100}%;"
              title="Sound: {effect.type} at {formatTime(effect.start)}"
            >
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
    <span class="text-xs font-mono text-dark-text-light">
      {formatTime(currentTime)}
    </span>
  </div>
</div>
