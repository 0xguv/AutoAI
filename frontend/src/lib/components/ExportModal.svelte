<script>
  import { uiState } from '../stores/uiStore';
  import { currentProject } from '../stores/projectStore';
  import { fade, scale } from 'svelte/transition';

  let exportSettings = {
    resolution: '1080x1920',
    fps: 30,
    quality: 'high'
  };

  // State
  let step = 'settings'; // 'settings' | 'processing' | 'complete' | 'error'
  let progress = 0;
  let statusMessage = '';
  let downloadUrl = '';
  let errorMessage = '';

  $: isOpen = $uiState.isExporting;

  async function startExport() {
    if (!$currentProject) return;
    
    step = 'processing';
    progress = 0;
    statusMessage = 'Starting export...';
    downloadUrl = '';
    errorMessage = '';

    try {
      const response = await fetch(`/api/export/${$currentProject.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: exportSettings,
          style: $currentProject.style,
          captions: $currentProject.captions
        })
      });

      if (!response.ok) {
        throw new Error('Export request failed');
      }

      const data = await response.json();
      console.log('Export started:', data);
      
      // Poll for progress
      pollStatus(data.export_id);

    } catch (err) {
      step = 'error';
      errorMessage = err.message;
    }
  }

  function pollStatus(exportId) {
    const checkStatus = async () => {
      try {
        const res = await fetch(`/api/export/status/${exportId}`);
        const status = await res.json();
        
        console.log('Status:', status);
        
        progress = status.progress || 0;
        statusMessage = status.message || 'Processing...';
        
        if (status.status === 'completed') {
          step = 'complete';
          progress = 100;
          downloadUrl = status.download_url || '';
          console.log('COMPLETE! Download URL:', downloadUrl);
        } else if (status.status === 'failed') {
          step = 'error';
          errorMessage = status.message || 'Export failed';
        } else {
          // Still processing, poll again
          setTimeout(checkStatus, 2000);
        }
      } catch (err) {
        console.error('Poll error:', err);
        setTimeout(checkStatus, 2000);
      }
    };
    
    checkStatus();
  }

  function downloadVideo() {
    if (!downloadUrl) return;
    
    const fullUrl = downloadUrl.startsWith('http') 
      ? downloadUrl 
      : `${window.location.origin}${downloadUrl}`;
    
    console.log('Downloading:', fullUrl);
    
    // Try to force download by fetching the blob
    fetch(fullUrl)
      .then(response => response.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `video-${Date.now()}.mp4`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      })
      .catch(err => {
        console.error('Download failed:', err);
        // Fallback: open in new tab
        window.open(fullUrl, '_blank');
      });
  }
  
  function getFullVideoUrl() {
    if (!downloadUrl) return '';
    return downloadUrl.startsWith('http') 
      ? downloadUrl 
      : `${window.location.origin}${downloadUrl}`;
  }

  function closeModal() {
    if (step !== 'processing') {
      uiState.update(u => ({ ...u, isExporting: false }));
      // Reset state
      setTimeout(() => {
        step = 'settings';
        progress = 0;
        statusMessage = '';
        downloadUrl = '';
        errorMessage = '';
      }, 300);
    }
  }
</script>

{#if isOpen}
  <div 
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center"
    on:click={closeModal}
    transition:fade={{ duration: 200 }}
  >
    <div 
      class="bg-dark-light rounded-2xl w-full max-w-2xl p-6 border border-dark-lighter"
      on:click|stopPropagation
      transition:scale={{ duration: 200, start: 0.95 }}
    >
      <h2 class="text-xl font-semibold text-white mb-4">Export Video</h2>

      {#if step === 'settings'}
        <!-- Settings Form -->
        <div class="space-y-4">
          <div>
            <label class="text-sm text-dark-text-light mb-2 block">Resolution</label>
            <div class="grid grid-cols-3 gap-2">
              {#each ['1080x1920', '1920x1080', '1080x1080'] as res}
                <button
                  class="p-2 rounded-lg border transition {exportSettings.resolution === res ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter'}"
                  on:click={() => exportSettings.resolution = res}
                >
                  {res === '1080x1920' ? '9:16' : res === '1920x1080' ? '16:9' : '1:1'}
                </button>
              {/each}
            </div>
          </div>

          <div>
            <label class="text-sm text-dark-text-light mb-2 block">Frame Rate</label>
            <div class="flex gap-2">
              {#each [24, 30, 60] as fps}
                <button
                  class="flex-1 p-2 rounded-lg border transition {exportSettings.fps === fps ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter'}"
                  on:click={() => exportSettings.fps = fps}
                >
                  {fps} FPS
                </button>
              {/each}
            </div>
          </div>

          <div class="flex gap-3 mt-6">
            <button 
              class="flex-1 p-3 rounded-lg border border-dark-lighter text-dark-text-light hover:bg-dark-lighter"
              on:click={closeModal}
            >
              Cancel
            </button>
            <button 
              class="flex-1 p-3 rounded-lg bg-primary text-white font-medium hover:bg-primary-dark"
              on:click={startExport}
            >
              Export
            </button>
          </div>
        </div>

      {:else if step === 'processing'}
        <!-- Processing -->
        <div class="text-center py-4">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-dark mb-4">
            <svg class="w-8 h-8 text-primary animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
          </div>
          <p class="text-lg font-medium text-white">{statusMessage}</p>
          <p class="text-sm text-dark-text-light mt-1">{progress}%</p>
          <div class="h-2 bg-dark-lighter rounded-full overflow-hidden mt-4">
            <div class="h-full bg-primary transition-all" style="width: {progress}%"/>
          </div>
        </div>

      {:else if step === 'complete'}
        <!-- Complete with Video Preview -->
        <div class="text-center">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/20 mb-3">
            <svg class="w-6 h-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <p class="text-lg font-medium text-white mb-3">Export Complete!</p>
          
          {#if downloadUrl}
            <!-- Video Preview -->
            <div class="relative rounded-lg overflow-hidden bg-black mb-3" style="max-height: 400px;">
              <video 
                controls 
                class="w-full max-h-[400px]"
                src={getFullVideoUrl()}
                poster=""
              >
                <track kind="captions" />
              </video>
            </div>
            
            <!-- Action Buttons -->
            <div class="flex gap-2">
              <button 
                class="flex-1 p-3 rounded-lg bg-green-500 text-white font-medium hover:bg-green-600 flex items-center justify-center gap-2"
                on:click={downloadVideo}
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
                Download
              </button>
              <a 
                href={getFullVideoUrl()}
                target="_blank"
                class="flex-1 p-3 rounded-lg bg-dark-lighter text-white font-medium hover:bg-dark border border-dark-lighter flex items-center justify-center gap-2"
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
                Open
              </a>
            </div>
          {:else}
            <p class="text-yellow-500 mb-3">Download URL not available</p>
          {/if}
          
          <button 
            class="w-full mt-3 p-2 rounded-lg border border-dark-lighter text-dark-text-light hover:bg-dark-lighter"
            on:click={closeModal}
          >
            Close
          </button>
        </div>

      {:else if step === 'error'}
        <!-- Error -->
        <div class="text-center py-4">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/20 mb-4">
            <svg class="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>
          <p class="text-lg font-medium text-white mb-2">Export Failed</p>
          <p class="text-sm text-dark-text-light mb-4">{errorMessage}</p>
          <button 
            class="w-full p-3 rounded-lg border border-dark-lighter text-dark-text-light hover:bg-dark-lighter"
            on:click={closeModal}
          >
            Close
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
