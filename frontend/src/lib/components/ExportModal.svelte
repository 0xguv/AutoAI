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

  $: isOpen = $uiState.isExporting;

  async function startExport() {
    if (!$currentProject) return;
    
    exporting = true;
    exportStatus = 'Preparing...';
    exportProgress = 0;

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

      if (!response.ok) throw new Error('Export failed');

      const data = await response.json();
      
      // Poll for progress
      const pollInterval = setInterval(async () => {
        const statusRes = await fetch(`/api/export/status/${data.export_id}`);
        const status = await statusRes.json();
        
        exportProgress = status.progress || 0;
        exportStatus = status.message || 'Processing...';

        if (status.status === 'completed') {
          clearInterval(pollInterval);
          exporting = false;
          window.open(status.download_url, '_blank');
          closeModal();
        } else if (status.status === 'failed') {
          clearInterval(pollInterval);
          exporting = false;
          exportStatus = 'Export failed';
        }
      }, 2000);

    } catch (err) {
      exporting = false;
      exportStatus = 'Export failed';
      console.error('Export error:', err);
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

      {#if exporting}
        <div class="space-y-4">
          <div class="text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-dark mb-4">
              <svg class="w-8 h-8 text-primary animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
            </div>
            <p class="text-lg font-medium text-white">{exportStatus}</p>
            <p class="text-sm text-dark-text-light mt-1">{exportProgress}% complete</p>
          </div>
          
          <div class="h-2 bg-dark-lighter rounded-full overflow-hidden">
            <div 
              class="h-full bg-primary transition-all duration-300"
              style="width: {exportProgress}%"
            />
          </div>
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
