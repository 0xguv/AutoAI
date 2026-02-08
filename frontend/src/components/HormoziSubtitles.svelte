<script>
  import { onMount, onDestroy, tick } from 'svelte'
  
  export let videoElement
  export let captions = []
  export let maxWordsPerLine = 4
  export let backgroundColor = '#FF0000'
  export let activeWordColor = '#FFFFFF'
  export let inactiveWordColor = 'rgba(255, 255, 255, 0.5)'
  export let fontSize = 'clamp(28px, 4vw, 56px)'
  export let enablePopAnimation = true
  export let popScale = 1.15
  
  let currentTime = 0
  let activeWordIndex = -1
  let visibleWords = []
  let isPlaying = false
  let rafId = null
  let mounted = false
  
  // Convert captions to word-level timestamps
  $: wordTimestamps = captions.flatMap(caption => {
    const words = caption.text.split(/\s+/).filter(w => w.trim())
    if (words.length === 0) return []
    
    const duration = caption.end - caption.start
    const wordDuration = duration / words.length
    
    return words.map((word, index) => ({
      word: word.replace(/[^\w\s]/gi, ''),
      start: caption.start + (index * wordDuration),
      end: caption.start + ((index + 1) * wordDuration),
    }))
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
    
    // Only update if changed to avoid infinite loops
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
    
    videoElement.addEventListener('play', handlePlay)
    videoElement.addEventListener('pause', handlePause)
    videoElement.addEventListener('timeupdate', handleTimeUpdate)
    videoElement.addEventListener('seeking', handleTimeUpdate)
    
    // Initial update
    handleTimeUpdate()
    
    return () => {
      videoElement.removeEventListener('play', handlePlay)
      videoElement.removeEventListener('pause', handlePause)
      videoElement.removeEventListener('timeupdate', handleTimeUpdate)
      videoElement.removeEventListener('seeking', handleTimeUpdate)
      listenersSetup = false
    }
  }
  
  onMount(() => {
    mounted = true
    console.log('HormoziSubtitles mounted, captions:', captions.length)
    if (captions.length > 0) {
      updateVisibleWords()
    }
  })
  
  onDestroy(() => {
    mounted = false
    if (rafId) cancelAnimationFrame(rafId)
  })
</script>

{#if visibleWords.length > 0}
  <div 
    class="hormozi-subtitles-container"
    style="font-size: {fontSize};"
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
  </div>
{/if}

<style>
  .hormozi-subtitles-container {
    position: absolute;
    bottom: 12%;
    left: 50%;
    transform: translateX(-50%);
    width: 95%;
    max-width: 900px;
    text-align: center;
    pointer-events: none;
    z-index: 100;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    font-weight: 900;
    letter-spacing: -0.02em;
    line-height: 1.2;
    text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.8);
  }

  .hormozi-subtitles-wrapper {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 0.2em;
    padding: 0.3em;
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
    font-size: 0.6em; /* Reduced from default to prevent oversized text */
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

  @media (max-width: 768px) {
    .hormozi-subtitles-container {
      bottom: 18%;
      width: 98%;
    }
    
    .hormozi-subtitles-wrapper {
      gap: 0.1em;
    }

    .hormozi-word {
      font-size: 0.5em;
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
