<script>
  import { onMount } from 'svelte'
  import { Play, Pause, Volume2, Maximize, SkipBack, SkipForward } from 'lucide-svelte'
  import Timeline from './Timeline.svelte'
  import HormoziSubtitles from './HormoziSubtitles.svelte'
  
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
  let videoContainerRef = null
  let originalFilename = ""
  
  // Export state
  let isExporting = false
  let exportStatus = ''
  let exportComplete = false
  let downloadUrl = ''
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
  
  // Fullscreen toggle - fullscreen the container, not just video
  function toggleFullscreen() {
    if (!videoContainerRef) return
    
    if (!document.fullscreenElement) {
      videoContainerRef.requestFullscreen().then(() => {
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
  
  // Prevent right-click on video
  function handleContextMenu(e) {
    e.preventDefault()
    return false
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
        originalFilename = data.original_filename || ''
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
    exportComplete = false
    
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
        exportStatus = 'Video burning in progress...'
        
        // Poll for burning completion
        const burnResult = await pollBurnStatus(data.job_id)
        
        exportComplete = true
        exportStatus = 'Export complete!'
        downloadUrl = burnResult.result?.video_url || ''
      } else {
        throw new Error(data.message || 'Failed to start export')
      }
    } catch (e) {
      console.error('Error exporting video:', e)
      exportStatus = `Export failed: ${e.message}`
      exportComplete = false
    } finally {
      isExporting = false
    }
  }
  
</script>

<div class="flex-1 flex flex-col ml-16 h-screen">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
    <h1 class="text-lg font-semibold text-gray-900">{originalFilename || 'Video Editor'}</h1>
    <div class="flex items-center space-x-3">
      {#if exportComplete && downloadUrl}
        <a href={downloadUrl} class="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors flex items-center space-x-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <span>Download Video</span>
        </a>
      {:else}
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
      {/if}
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
          <div 
            bind:this={videoContainerRef}
            class="relative h-full max-h-[calc(100vh-300px)] aspect-[9/16] bg-black rounded-lg overflow-hidden shadow-2xl"
            on:contextmenu|preventDefault={handleContextMenu}
          >
            <video
              bind:this={videoElement}
              class="w-full h-full object-contain"
              src={videoUrl}
              on:timeupdate={handleTimeUpdate}
              on:play={() => isPlaying = true}
              on:pause={() => isPlaying = false}
              on:contextmenu|preventDefault={handleContextMenu}
            >
              <track kind="captions" />
            </video>
            
            <!-- Hormozi-style Dynamic Subtitles -->
            {#if captions.length > 0 && videoElement}
              <HormoziSubtitles 
                {videoElement} 
                {captions}
                bind:position={subtitlePosition}
                maxWordsPerLine={3}
                backgroundColor="#FF0000"
                activeWordColor="#FFFFFF"
                inactiveWordColor="rgba(255, 255, 255, 0.4)"
                fontSize="clamp(20px, 3vw, 40px)"
                enablePopAnimation={true}
                popScale={1.1}
                on:positionChange={(e) => subtitlePosition = e.detail}
              />
            {/if}
          </div>
        </div>
        
        <!-- Controls Section -->
        <div class="flex flex-col items-center pb-4 px-4 space-y-3">
          <!-- Progress Bar / Timeline - narrower than controls -->
          <div class="w-full max-w-md">
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
          
          <!-- Video Controls - wider than progress bar -->
          <div class="flex items-center space-x-4 bg-gray-800 rounded-full px-8 py-3">
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
  
  @keyframes popIn {
    0% {
      opacity: 0;
      transform: scale(0.5) translateY(10px);
    }
    50% {
      transform: scale(1.1) translateY(-2px);
    }
    100% {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
  
  .animate-pop {
    animation: popIn 0.4s ease-out forwards;
    opacity: 0;
  }
</style>
