<script>
  import { uiState } from '../stores/uiStore';
  import { currentProject } from '../stores/projectStore';
  import { fade, scale } from 'svelte/transition';

  let exportSettings = {
    resolution: '1080x1920',
    fps: 30,
    quality: 'high'
  };

  let exporting = false;
  let exportProgress = 0;
  let exportStatus = '';
  let downloadUrl = null;
  let exportComplete = false;

  $: isOpen = $uiState.isExporting;

  async function startExport() {
    if (!$currentProject) return;
    
    exporting = true;
    exportStatus = 'Preparing...';
    exportProgress = 0;
    downloadUrl = null;
    exportComplete = false;

    try {
      console.log('Starting export for project:', $currentProject.id);
      
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
        const errorData = await response.json();
        throw new Error(errorData.message || 'Export failed');
      }

      const data = await response.json();
      console.log('Export queued:', data);
      
      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/export/status/${data.export_id}`);
          const status = await statusRes.json();
          
          console.log('Export status:', status);
          
          exportProgress = status.progress || 0;
          exportStatus = status.message || 'Processing...';
          
          if (status.download_url) {
            downloadUrl = status.download_url;
          }

          if (status.status === 'completed') {
            clearInterval(pollInterval);
            console.log('Export COMPLETED! download_url:', status.download_url);
            exporting = false;
            exportComplete = true;
            if (status.download_url) {
              downloadUrl = status.download_url;
              console.log('Set downloadUrl to:', downloadUrl);
            }
            exportStatus = 'Export complete!';
            exportProgress = 100;
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            exporting = false;
            exportComplete = false;
            exportStatus = status.message || 'Export failed';
          }
        } catch (pollErr) {
          console.error('Polling error:', pollErr);
        }
      }, 2000);

    } catch (err) {
      exporting = false;
      exportComplete = false;
      exportStatus = `Error: ${err.message}`;
      console.error('Export error:', err);
    }
  }

  async function handleDownload() {
    if (!downloadUrl) return;
    
    // Ensure full URL
    const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `${window.location.origin}${downloadUrl}`;
    console.log('Downloading from:', fullUrl);
    
    try {
      // Fetch the file
      const response = await fetch(fullUrl);
      if (!response.ok) throw new Error('Download failed');
      
      // Get blob
      const blob = await response.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `video-${Date.now()}.mp4`;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download error:', err);
      // Fallback: open in new tab
      window.open(fullUrl, '_blank');
    }
  }

  function closeModal() {
    if (!exporting) {
      uiState.update(u => ({ ...u, isExporting: false }));
    }
  }
</script>

{#if isOpen}
  <div 
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center"
    on:click={closeModal}
    on:keydown={(e) => e.key === 'Escape' && closeModal()}
    transition:fade={{ duration: 200 }}
    role="dialog"
    aria-modal="true"
  >
    <div 
      class="bg-dark-light rounded-2xl w-full max-w-md p-6 border border-dark-lighter"
      on:click|stopPropagation
      transition:scale={{ duration: 200, start: 0.95 }}
    >
      <h2 class="text-xl font-semibold text-white mb-4">Export Video</h2>

      {#if exporting || exportComplete}
        <div class="space-y-4">
          <div class="text-center">
            {#if exportComplete}
              <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/20 mb-4">
                <svg class="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
              </div>
            {:else}
              <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-dark mb-4">
                <svg class="w-8 h-8 text-primary animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
              </div>
            {/if}
            <p class="text-lg font-medium text-white">{exportStatus}</p>
            {#if !exportComplete}
              <p class="text-sm text-dark-text-light mt-1">{exportProgress}% complete</p>
            {/if}
          </div>
          
          <div class="h-2 bg-dark-lighter rounded-full overflow-hidden">
            <div 
              class="h-full bg-primary transition-all duration-300"
              style="width: {exportProgress}%"
            />
          </div>

          {#if exportComplete}
            {#if downloadUrl}
              <button 
                class="w-full p-3 rounded-lg bg-green-500 text-white font-medium hover:bg-green-600 transition flex items-center justify-center gap-2"
                on:click={handleDownload}
              >
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
                Download Video
              </button>
            {:else}
              <p class="text-yellow-500 text-sm">Export complete but download URL not available</p>
            {/if}
            <button 
              class="w-full p-2 rounded-lg border border-dark-lighter text-dark-text-light hover:bg-dark-lighter transition"
              on:click={closeModal}
            >
              Close
            </button>
          {/if}
        </div>
      {:else}
        <div class="space-y-4">
          <div>
            <label class="text-sm text-dark-text-light mb-2 block">Resolution</label>
            <div class="grid grid-cols-3 gap-2">
              {#each ['1080x1920', '1920x1080', '1080x1080'] as res}
                <button
                  class="p-2 rounded-lg border transition {exportSettings.resolution === res ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter hover:border-primary'}"
                  on:click={() => exportSettings.resolution = res}
                >
                  {res.split('x')[0] === '1080' && res.split('x')[1] === '1920' ? '9:16' : 
                   res.split('x')[0] === '1920' ? '16:9' : '1:1'}
                </button>
              {/each}
            </div>
          </div>

          <div>
            <label class="text-sm text-dark-text-light mb-2 block">Frame Rate</label>
            <div class="flex gap-2">
              {#each [24, 30, 60] as fps}
                <button
                  class="flex-1 p-2 rounded-lg border transition {exportSettings.fps === fps ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter hover:border-primary'}"
                  on:click={() => exportSettings.fps = fps}
                >
                  {fps} FPS
                </button>
              {/each}
            </div>
          </div>

          <div>
            <label class="text-sm text-dark-text-light mb-2 block">Quality</label>
            <div class="flex gap-2">
              {#each ['standard', 'high', 'ultra'] as quality}
                <button
                  class="flex-1 p-2 rounded-lg border transition {exportSettings.quality === quality ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter hover:border-primary'}"
                  on:click={() => exportSettings.quality = quality}
                >
                  {quality.charAt(0).toUpperCase() + quality.slice(1)}
                </button>
              {/each}
            </div>
          </div>

          <div class="flex gap-3 mt-6">
            <button 
              class="flex-1 p-3 rounded-lg border border-dark-lighter text-dark-text-light hover:bg-dark-lighter transition"
              on:click={closeModal}
            >
              Cancel
            </button>
            <button 
              class="flex-1 p-3 rounded-lg bg-primary text-white font-medium hover:bg-primary-dark transition"
              on:click={startExport}
            >
              Export
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}
