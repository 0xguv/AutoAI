<script>
  import { onMount, onDestroy } from 'svelte'
  
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
  let lastTime = 0
  let wordElements = []
  
  // Convert captions to word-level timestamps
  $: wordTimestamps = captions.flatMap(caption => {
    const words = caption.text.split(/\s+/).filter(w => w.trim())
    const duration = caption.end - caption.start
    const wordDuration = duration / words.length
    
    return words.map((word, index) => ({
      word: word.replace(/[^\w\s]/gi, ''), // Remove punctuation
      start: caption.start + (index * wordDuration),
      end: caption.start + ((index + 1) * wordDuration),
      originalWord: word
    }))
  })
  
  // Group words into chunks
  $: wordChunks = (() => {
    const chunks = []
    for (let i = 0; i < wordTimestamps.length; i += maxWordsPerLine) {
      chunks.push(wordTimestamps.slice(i, i + maxWordsPerLine))
    }
    return chunks
  })()
  
  function findActiveWordIndex(time) {
    return wordTimestamps.findIndex(
      word => time >= word.start && time <= word.end
    )
  }
  
  function animationLoop() {
    if (!videoElement) return
    
    const now = performance.now()
    const videoTime = videoElement.currentTime
    
    // Throttle to 60fps
    if (now - lastTime >= 16) {
      currentTime = videoTime
      
      const newActiveIndex = findActiveWordIndex(videoTime)
      
      if (newActiveIndex !== activeWordIndex) {
        activeWordIndex = newActiveIndex
        
        // Update visible chunk
        const chunkIndex = Math.floor(newActiveIndex / maxWordsPerLine)
        const startIdx = chunkIndex * maxWordsPerLine
        const endIdx = Math.min(startIdx + maxWordsPerLine, wordTimestamps.length)
        visibleWords = wordTimestamps.slice(startIdx, endIdx)
      }
      
      lastTime = now
    }
    
    if (isPlaying) {
      rafId = requestAnimationFrame(animationLoop)
    }
  }
  
  onMount(() => {
    if (!videoElement) return
    
    const handlePlay = () => {
      isPlaying = true
      rafId = requestAnimationFrame(animationLoop)
    }
    
    const handlePause = () => {
      isPlaying = false
      if (rafId) cancelAnimationFrame(rafId)
    }
    
    const handleTimeUpdate = () => {
      if (!isPlaying) {
        currentTime = videoElement.currentTime
        activeWordIndex = findActiveWordIndex(currentTime)
        const chunkIndex = Math.floor(activeWordIndex / maxWordsPerLine)
        const startIdx = chunkIndex * maxWordsPerLine
        const endIdx = Math.min(startIdx + maxWordsPerLine, wordTimestamps.length)
        visibleWords = wordTimestamps.slice(startIdx, endIdx)
      }
    }
    
    videoElement.addEventListener('play', handlePlay)
    videoElement.addEventListener('pause', handlePause)
    videoElement.addEventListener('timeupdate', handleTimeUpdate)
    videoElement.addEventListener('seeking', handleTimeUpdate)
    
    // Initial visible words
    if (wordTimestamps.length > 0) {
      visibleWords = wordTimestamps.slice(0, maxWordsPerLine)
    }
    
    return () => {
      videoElement.removeEventListener('play', handlePlay)
      videoElement.removeEventListener('pause', handlePause)
      videoElement.removeEventListener('timeupdate', handleTimeUpdate)
      videoElement.removeEventListener('seeking', handleTimeUpdate)
      if (rafId) cancelAnimationFrame(rafId)
    }
  })
  
  onDestroy(() => {
    if (rafId) cancelAnimationFrame(rafId)
  })
  
  $: {
    // Reset when captions change
    if (wordTimestamps.length > 0 && visibleWords.length === 0) {
      visibleWords = wordTimestamps.slice(0, maxWordsPerLine)
    }
  }
</script>

<div 
  class="hormozi-subtitles-container"
  style="font-size: {fontSize};"
>
  <div class="hormozi-subtitles-wrapper">
    {#each visibleWords as wordData, localIndex}
      {#if wordData}
        {@const globalIndex = Math.floor(activeWordIndex / maxWordsPerLine) * maxWordsPerLine + localIndex}
        {@const isActive = globalIndex === activeWordIndex}
        {@const isPast = globalIndex < activeWordIndex}
        
        <span
          bind:this={wordElements[localIndex]}
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
      {/if}
    {/each}
  </div>
</div>

<style>
  .hormozi-subtitles-container {
    position: absolute;
    bottom: 15%;
    left: 50%;
    transform: translateX(-50%);
    width: 90%;
    max-width: 1000px;
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
    gap: 0.25em;
    padding: 0.5em;
  }

  .hormozi-word {
    display: inline-block;
    padding: 0.12em 0.2em;
    border-radius: 0.08em;
    transition: all 0.12s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform, color, background-color;
    transform-origin: center center;
    white-space: nowrap;
    backface-visibility: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
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
      transform: scale(0.85);
      opacity: 0.7;
    }
    50% {
      transform: scale(1.2);
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }

  .pop-animation {
    animation: wordPop 0.25s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
  }

  @media (max-width: 768px) {
    .hormozi-subtitles-container {
      bottom: 20%;
      width: 95%;
    }
    
    .hormozi-subtitles-wrapper {
      gap: 0.15em;
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
