<script>
  import { onMount } from 'svelte'
  import { Play, Pause, Volume2, Maximize, SkipBack, SkipForward } from 'lucide-svelte'
  import Timeline from './Timeline.svelte'
  
  export let jobId

  let videoElement
  let isPlaying = false
  let currentTime = 0
  let duration = 0
  let volume = 1
  let videoUrl = ''
  let isFullscreen = false
  
  let loading = true
  let error = null

  // Subtitle state
  let subtitlePosition = { x: 50, y: 15 }
  let subtitleText = ""
  let isDragging = false
  let dragStart = { x: 0, y: 0 }
  let subtitleRef = null
  
  // Export state
  let isExporting = false
  let exportStatus = ''
  let resolution = 'original'
  
  function togglePlay() {
    if (videoElement) {
      if (isPlaying) {
        videoElement.pause()
      } else {
        videoElement.play()
      }
    }
  }
  
  function handleTimeUpdate() {
    if (videoElement) {
      currentTime = videoElement.currentTime
      duration = videoElement.duration || 0
      
      // Update active caption based on current time
      captions = captions.map(c => ({
        ...c,
        active: currentTime >= c.start && currentTime <= c.end
      }))
      
      // Update subtitleText from active caption
      const activeCaption = captions.find(c => c.active)
      subtitleText = activeCaption ? activeCaption.text : ""
    }
  }
  
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  // Fixed drag handler - centers subtitle on cursor
  function handleSubtitleMouseDown(e) {
    e.preventDefault()
    e.stopPropagation()
    
    if (!subtitleRef) return
    
    isDragging = true
    
    const rect = subtitleRef.getBoundingClientRect()
    const parentRect = subtitleRef.parentElement.getBoundingClientRect()
    
    // Calculate offset from center of subtitle to cursor
    dragStart = {
      offsetX: e.clientX - (rect.left + rect.width / 2),
      offsetY: e.clientY - (rect.top + rect.height / 2),
      parentWidth: parentRect.width,
      parentHeight: parentRect.height
    }
  }
  
  function handleMouseMove(e) {
    if (!isDragging || !subtitleRef) return
    
    const parentRect = subtitleRef.parentElement.getBoundingClientRect()
    
    // Calculate new position relative to parent center
    const centerX = e.clientX - dragStart.offsetX - parentRect.left
    const centerY = e.clientY - dragStart.offsetY - parentRect.top
    
    // Convert to percentage
    const x = (centerX / parentRect.width) * 100
    const y = 100 - ((centerY / parentRect.height) * 100)
    
    // Constrain to keep subtitle visible
    subtitlePosition.x = Math.max(5, Math.min(95, x))
    subtitlePosition.y = Math.max(5, Math.min(95, y))
  }
  
  function handleMouseUp() {
    isDragging = false
  }
  
  // Fullscreen toggle
  function toggleFullscreen() {
    if (!videoElement) return
    
    if (!document.fullscreenElement) {
      videoElement.requestFullscreen().then(() => {
        isFullscreen = true
      }).catch(err => {
        console.error('Error attempting to enable fullscreen:', err)
      })
    } else {
      document.exitFullscreen().then(() => {
        isFullscreen = false
      }).catch(err => {
        console.error('Error attempting to exit fullscreen:', err)
      })
    }
  }
  
  // Seek to position on progress bar click
  function handleProgressClick(e) {
    if (!videoElement || !duration) return
    
    const rect = e.currentTarget.getBoundingClientRect()
    const clickPosition = (e.clientX - rect.left) / rect.width
    const newTime = clickPosition * duration
    
    videoElement.currentTime = newTime
    currentTime = newTime
  }
  
  // Captions data
  let captions = []
  
  function srtTimeToSeconds(srtTime) {
    const [hours, minutes, secondsAndMillis] = srtTime.split(':')
    const [seconds, millis] = secondsAndMillis.split(',')
    return parseInt(hours, 10) * 3600 +
           parseInt(minutes, 10) * 60 +
           parseInt(seconds, 10) +
           parseInt(millis, 10) / 1000
  }

  function parseSrt(srtContent) {
    const lines = srtContent.split(/\r?\n/)
    let parsedCaptions = []
    let currentCaption = null
    let idCounter = 1

    for (const line of lines) {
      if (line.trim() === '') {
        if (currentCaption && currentCaption.text.trim() !== '') {
          parsedCaptions.push(currentCaption)
        }
        currentCaption = null
      } else if (currentCaption === null) {
        currentCaption = { id: idCounter++, text: '', active: false }
      } else if (line.includes('-->')) {
        const [startTime, endTime] = line.split('-->').map(s => s.trim())
        currentCaption.start = srtTimeToSeconds(startTime)
        currentCaption.end = srtTimeToSeconds(endTime)
      } else {
        currentCaption.text += (currentCaption.text === '' ? '' : ' ') + line.trim()
      }
    }
    if (currentCaption && currentCaption.text.trim() !== '') {
      parsedCaptions.push(currentCaption)
    }
    return parsedCaptions
  }

  onMount(async () => {
    try {
      const response = await fetch(`/api/editor_data/${jobId}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      if (data.status === 'success') {
        videoUrl = data.video_url
        captions = parseSrt(data.srt_content)
        resolution = data.resolution || 'original'
      } else {
        throw new Error(data.message || 'Failed to load editor data')
      }
    } catch (e) {
      console.error("Error fetching editor data:", e)
      error = e.message
    } finally {
      loading = false
    }
  })
  
  function handleCaptionUpdate(id, newText) {
    captions = captions.map(c => c.id === id ? { ...c, text: newText } : c)
  }
  
  function handleCaptionClick(caption) {
    if (videoElement) {
      videoElement.currentTime = caption.start
    }
  }
  
  function secondsToSrtTime(seconds) {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    const millis = Math.floor((seconds % 1) * 1000)
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${millis.toString().padStart(3, '0')}`
  }

  function generateSrtContent() {
    return captions.map((caption, index) => {
      return `${index + 1}\n${secondsToSrtTime(caption.start)} --> ${secondsToSrtTime(caption.end)}\n${caption.text}`
    }).join('\n\n')
  }

  async function pollBurnStatus(originalJobId) {
    return new Promise((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`/api/job_status/${originalJobId}`)
          const data = await response.json()
          
          if (data.status === 'completed') {
            clearInterval(pollInterval)
            resolve(data)
          } else if (data.status === 'failed') {
            clearInterval(pollInterval)
            reject(new Error(data.error || 'Burning failed'))
          } else {
            exportStatus = `Processing: ${data.progress_message || data.status}...`
          }
        } catch (e) {
          clearInterval(pollInterval)
          reject(e)
        }
      }, 3000)
      
      setTimeout(() => {
        clearInterval(pollInterval)
        reject(new Error('Export timed out'))
      }, 600000)
    })
  }

  async function handleExport() {
    isExporting = true
    exportStatus = 'Saving subtitles...'
    
    try {
      const srtContent = generateSrtContent()
      const positionalData = {
        x: subtitlePosition.x,
        y: subtitlePosition.y
      }
      
      const response = await fetch('/save_and_burn', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_id: jobId,
          srt_content: srtContent,
          positional_data: positionalData,
          resolution: resolution
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.status === 'success') {
        exportStatus = 'Video burning started. Please wait...'
        
        // Poll for burning completion
        const burnResult = await pollBurnStatus(data.job_id)
        
        exportStatus = 'Export complete! Redirecting...'
        
        setTimeout(() => {
          window.location.href = '/'
        }, 2000)
      } else {
        throw new Error(data.message || 'Failed to start export')
      }
    } catch (e) {
      console.error('Error exporting video:', e)
      exportStatus = `Export failed: ${e.message}`
    } finally {
      setTimeout(() => {
        isExporting = false
      }, 5000)
    }
  }
  
  // Split subtitle text into words for red boxes
  $: subtitleWords = subtitleText ? subtitleText.split(' ').filter(w => w.trim()) : []
</script>

<svelte:window on:mousemove={handleMouseMove} on:mouseup={handleMouseUp} />

<div class="flex-1 flex flex-col ml-16 h-screen">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
    <h1 class="text-lg font-semibold text-gray-900">Video Editor ({jobId})</h1>
    <div class="flex items-center space-x-3">
      {#if exportStatus}
        <span class="text-sm {exportStatus.includes('failed') ? 'text-red-600' : 'text-green-600'}">{exportStatus}</span>
      {/if}
      <button 
        class="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        on:click={handleExport}
        disabled={isExporting}
      >
        {isExporting ? 'Exporting...' : 'Export Video'}
      </button>
    </div>
  </header>

  <!-- Main content area -->
  {#if loading}
    <div class="flex-1 flex items-center justify-center text-gray-500 text-xl">Loading editor...</div>
  {:else if error}
    <div class="flex-1 flex items-center justify-center text-red-500 text-xl">Error: {error}</div>
  {:else}
    <div class="flex-1 flex overflow-hidden">
      <!-- Video Player Section -->
      <div class="flex-1 flex flex-col bg-gray-900">
        <!-- Video Container -->
        <div class="flex-1 flex items-center justify-center p-4 overflow-hidden">
          <div class="relative h-full max-h-[calc(100vh-280px)] aspect-[9/16] bg-black rounded-lg overflow-hidden shadow-2xl">
            <video
              bind:this={videoElement}
              class="w-full h-full object-contain"
              src={videoUrl}
              on:timeupdate={handleTimeUpdate}
              on:play={() => isPlaying = true}
              on:pause={() => isPlaying = false}
            >
              <track kind="captions" />
            </video>
            
            <!-- Red Word Boxes Subtitle Overlay -->
            {#if subtitleWords.length > 0}
              <div
                bind:this={subtitleRef}
                class="absolute flex flex-wrap justify-center gap-1 cursor-move select-none px-2"
                style="left: {subtitlePosition.x}%; bottom: {subtitlePosition.y}%; transform: translate(-50%, 0); max-width: 90%;"
                on:mousedown={handleSubtitleMouseDown}
                role="button"
                tabindex="0"
              >
                {#each subtitleWords as word}
                  <span class="bg-red-600 text-white px-2 py-1 rounded text-lg font-medium whitespace-nowrap">
                    {word}
                  </span>
                {/each}
                
                <!-- Position indicator -->
                <div class="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  {Math.round(subtitlePosition.x)}%, {Math.round(subtitlePosition.y)}%
                </div>
              </div>
            {/if}
          </div>
        </div>
        
        <!-- Controls Section -->
        <div class="flex flex-col items-center pb-4 px-4 space-y-3">
          <!-- Progress Bar / Timeline -->
          <div class="w-full max-w-lg">
            <div 
              class="h-2 bg-gray-700 rounded-full cursor-pointer relative overflow-hidden"
              on:click={handleProgressClick}
              role="slider"
              aria-valuenow={currentTime}
              aria-valuemax={duration}
              tabindex="0"
            >
              <div 
                class="h-full bg-green-500 rounded-full transition-all duration-100"
                style="width: {(currentTime / (duration || 1)) * 100}%"
              ></div>
            </div>
            <div class="flex justify-between text-xs text-gray-400 mt-1">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
          
          <!-- Video Controls -->
          <div class="flex items-center space-x-4 bg-gray-800 rounded-full px-6 py-3">
            <button 
              class="text-gray-400 hover:text-white transition-colors"
              on:click={() => videoElement && (videoElement.currentTime -= 5)}
            >
              <SkipBack class="w-5 h-5" />
            </button>
            
            <button 
              class="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-900 hover:bg-gray-200 transition-colors"
              on:click={togglePlay}
            >
              {#if isPlaying}
                <Pause class="w-5 h-5" />
              {:else}
                <Play class="w-5 h-5 ml-0.5" />
              {/if}
            </button>
            
            <button 
              class="text-gray-400 hover:text-white transition-colors"
              on:click={() => videoElement && (videoElement.currentTime += 5)}
            >
              <SkipForward class="w-5 h-5" />
            </button>
            
            <div class="w-px h-6 bg-gray-600 mx-2"></div>
            
            <span class="text-gray-300 text-sm font-mono min-w-[100px]">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
            
            <div class="flex items-center space-x-2">
              <Volume2 class="w-4 h-4 text-gray-400" />
              <input 
                type="range" 
                min="0" 
                max="1" 
                step="0.1"
                bind:value={volume}
                on:input={() => videoElement && (videoElement.volume = volume)}
                class="w-20 accent-green-500"
              />
            </div>
            
            <button 
              class="text-gray-400 hover:text-white transition-colors ml-2"
              on:click={toggleFullscreen}
            >
              <Maximize class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Timeline Panel -->
      <Timeline 
        {captions} 
        {currentTime}
        onUpdate={handleCaptionUpdate}
        onCaptionClick={handleCaptionClick}
      />
    </div>
  {/if}
</div>

<style>
  .select-none {
    user-select: none;
    -webkit-user-select: none;
  }
</style>
