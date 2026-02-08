<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte'
  
  export let videoElement
  export let captions = []
  export let maxWordsPerLine = 4
  export let backgroundColor = '#FF0000'
  export let activeWordColor = '#FFFFFF'
  export let inactiveWordColor = 'rgba(255, 255, 255, 0.5)'
  export let fontSize = 'clamp(28px, 4vw, 56px)'
  export let enablePopAnimation = true
  export let popScale = 1.15
  export let position = { x: 50, y: 15 }
  
  const dispatch = createEventDispatcher()
  
  let currentTime = 0
  let activeWordIndex = -1
  let visibleWords = []
  let isPlaying = false
  let rafId = null
  let mounted = false
  let containerRef = null
  let isDragging = false
  let dragStart = { mouseX: 0, mouseY: 0, posX: 0, posY: 0 }
  
  // Convert captions to word-level timestamps with variable timing
  $: wordTimestamps = captions.flatMap(caption => {
    const words = caption.text.split(/\s+/).filter(w => w.trim())
    if (words.length === 0) return []
    
    const duration = caption.end - caption.start
    
    // Calculate word weights based on length (longer words need more time)
    const wordWeights = words.map(word => Math.max(1, word.length * 0.5))
    const totalWeight = wordWeights.reduce((sum, w) => sum + w, 0)
    
    let currentTime = caption.start
    
    return words.map((word, index) => {
      const weight = wordWeights[index]
      const wordDuration = (weight / totalWeight) * duration
      const start = currentTime
      const end = currentTime + wordDuration
      currentTime = end
      
      return {
        word: word.replace(/[^\w\s]/gi, ''),
        start,
        end,
        originalWord: word
      }
    })
  })
  
  // Find active word index based on current time
  function findActiveWordIndex(time) {
    if (!wordTimestamps || wordTimestamps.length === 0) return -1
    return wordTimestamps.findIndex(
      word => time >= word.start && time <= word.end
    )
  }
  
  // Calculate visible words based on active word
  function updateVisibleWords() {
    if (wordTimestamps.length === 0) {
      visibleWords = []
      return
    }
    
    const effectiveIndex = activeWordIndex >= 0 ? activeWordIndex : 0
    const chunkIndex = Math.floor(effectiveIndex / maxWordsPerLine)
    const startIdx = chunkIndex * maxWordsPerLine
    const endIdx = Math.min(startIdx + maxWordsPerLine, wordTimestamps.length)
    
    const newVisible = wordTimestamps.slice(startIdx, endIdx)
    if (JSON.stringify(newVisible) !== JSON.stringify(visibleWords)) {
      visibleWords = newVisible
    }
  }
  
  // Animation loop for smooth updates
  function animationLoop() {
    if (!videoElement || !mounted) return
    
    const videoTime = videoElement.currentTime
    currentTime = videoTime
    
    const newActiveIndex = findActiveWordIndex(videoTime)
    if (newActiveIndex !== activeWordIndex) {
      activeWordIndex = newActiveIndex
      updateVisibleWords()
    }
    
    if (isPlaying) {
      rafId = requestAnimationFrame(animationLoop)
    }
  }
  
  // Drag handlers
  function handleMouseDown(e) {
    e.preventDefault()
    e.stopPropagation()
    
    if (!containerRef) return
    
    isDragging = true
    dragStart = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      posX: position.x,
      posY: position.y
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
  }
  
  function handleMouseMove(e) {
    if (!isDragging) return
    
    const deltaX = e.clientX - dragStart.mouseX
    const deltaY = e.clientY - dragStart.mouseY
    
    // Convert to percentage (rough estimate based on screen size)
    const parentRect = containerRef.parentElement?.getBoundingClientRect()
    if (parentRect) {
      position.x = Math.max(5, Math.min(95, dragStart.posX + (deltaX / parentRect.width) * 100))
      position.y = Math.max(5, Math.min(50, dragStart.posY - (deltaY / parentRect.height) * 100))
    }
  }
  
  function handleMouseUp() {
    isDragging = false
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
    
    // Dispatch position change event
    dispatch('positionChange', { x: position.x, y: position.y })
  }
  
  // React to caption changes
  $: if (captions && captions.length > 0 && mounted) {
    updateVisibleWords()
  }
  
  // React to videoElement changes
  $: if (videoElement && mounted) {
    setupVideoListeners()
  }
  
  let listenersSetup = false
  function setupVideoListeners() {
    if (listenersSetup || !videoElement) return
    listenersSetup = true
    
    const handlePlay = () => {
      isPlaying = true
      if (rafId) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(animationLoop)
    }
    
    const handlePause = () => {
      isPlaying = false
      if (rafId) cancelAnimationFrame(rafId)
    }
    
    const handleTimeUpdate = () => {
      if (!isPlaying && videoElement) {
        currentTime = videoElement.currentTime
        const newIndex = findActiveWordIndex(currentTime)
        if (newIndex !== activeWordIndex) {
          activeWordIndex = newIndex
          updateVisibleWords()
        }
      }
    }
    
    // Prevent right-click
    const handleContextMenu = (e) => {
      e.preventDefault()
      return false
    }
    
    videoElement.addEventListener('play', handlePlay)
    videoElement.addEventListener('pause', handlePause)
    videoElement.addEventListener('timeupdate', handleTimeUpdate)
    videoElement.addEventListener('seeking', handleTimeUpdate)
    videoElement.addEventListener('contextmenu', handleContextMenu)
    
    // Initial update
    handleTimeUpdate()
    
    return () => {
      videoElement.removeEventListener('play', handlePlay)
      videoElement.removeEventListener('pause', handlePause)
      videoElement.removeEventListener('timeupdate', handleTimeUpdate)
      videoElement.removeEventListener('seeking', handleTimeUpdate)
      videoElement.removeEventListener('contextmenu', handleContextMenu)
      listenersSetup = false
    }
  }
  
  onMount(() => {
    mounted = true
    if (captions.length > 0) {
      updateVisibleWords()
    }
  })
  
  onDestroy(() => {
    mounted = false
    if (rafId) cancelAnimationFrame(rafId)
    window.removeEventListener('mousemove', handleMouseMove)
    window.removeEventListener('mouseup', handleMouseUp)
  })
</script>

{#if visibleWords.length > 0}
  <div 
    bind:this={containerRef}
    class="hormozi-subtitles-container"
    class:dragging={isDragging}
    style="font-size: {fontSize}; left: {position.x}%; bottom: {position.y}%;"
    on:mousedown={handleMouseDown}
    role="button"
    tabindex="0"
    aria-label="Drag to reposition subtitles"
  >
    <div class="hormozi-subtitles-wrapper">
      {#each visibleWords as wordData, localIndex (`${wordData.start}-${wordData.word}`)}
        {@const globalIndex = Math.floor((activeWordIndex >= 0 ? activeWordIndex : 0) / maxWordsPerLine) * maxWordsPerLine + localIndex}
        {@const isActive = globalIndex === activeWordIndex}
        {@const isPast = globalIndex < activeWordIndex}
        
        <span
          class="hormozi-word"
          class:active={isActive}
          class:past={isPast}
          class:pop-animation={enablePopAnimation && isActive}
          style="
            color: {isActive ? activeWordColor : inactiveWordColor};
            background-color: {isActive ? backgroundColor : 'transparent'};
            transform: {isActive && enablePopAnimation ? `scale(${popScale})` : 'scale(1)'};
          "
        >
          {wordData.word.toUpperCase()}
        </span>
      {/each}
    </div>
    
    <!-- Position indicator -->
    <div class="position-indicator">
      {Math.round(position.x)}%, {Math.round(position.y)}%
    </div>
  </div>
{/if}

<style>
  .hormozi-subtitles-container {
    position: absolute;
    /* left and bottom set via inline styles */
    transform: translateX(-50%);
    width: 95%;
    max-width: 900px;
    text-align: center;
    cursor: grab;
    z-index: 100;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    font-weight: 900;
    letter-spacing: -0.02em;
    line-height: 1.2;
    text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.8);
  }

  .hormozi-subtitles-container:hover .position-indicator {
    opacity: 1;
  }

  .hormozi-subtitles-container.dragging {
    cursor: grabbing;
  }

  .hormozi-subtitles-wrapper {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 0.2em;
    padding: 0.3em;
    pointer-events: none;
  }

  .hormozi-word {
    display: inline-block;
    padding: 0.1em 0.15em;
    border-radius: 0.08em;
    transition: all 0.08s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform, color, background-color;
    transform-origin: center center;
    white-space: nowrap;
    backface-visibility: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-size: 0.8em;
    pointer-events: none;
  }

  .hormozi-word.active {
    box-shadow: 
      0 4px 8px rgba(0, 0, 0, 0.4),
      0 12px 24px rgba(0, 0, 0, 0.3);
    z-index: 10;
  }

  .hormozi-word.past {
    opacity: 0.5;
    transform: scale(0.95);
  }

  @keyframes wordPop {
    0% {
      transform: scale(0.9);
      opacity: 0.8;
    }
    50% {
      transform: scale(1.1);
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }

  .pop-animation {
    animation: wordPop 0.15s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
  }

  .position-indicator {
    position: absolute;
    top: -25px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
    white-space: nowrap;
    font-weight: normal;
  }

  /* Fullscreen adjustments */
  :global(:fullscreen) .hormozi-subtitles-container,
  :global(:-webkit-full-screen) .hormozi-subtitles-container,
  :global(:-moz-full-screen) .hormozi-subtitles-container {
    font-size: clamp(40px, 5vw, 80px) !important;
    max-width: 1200px;
  }

  :global(:fullscreen) .hormozi-word,
  :global(:-webkit-full-screen) .hormozi-word,
  :global(:-moz-full-screen) .hormozi-word {
    font-size: 1em !important;
  }

  @media (max-width: 768px) {
    .hormozi-subtitles-container {
      width: 98%;
    }
    
    .hormozi-subtitles-wrapper {
      gap: 0.1em;
    }

    .hormozi-word {
      font-size: 0.6em;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .hormozi-word {
      transition: none;
    }
    
    .pop-animation {
      animation: none;
    }
  }
</style>
