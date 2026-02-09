<script>
  import { onMount } from 'svelte';
  import { currentProject, videoState, uiState } from './lib/stores/editor';
  import Sidebar from './lib/components/Sidebar.svelte';
  import EditorLayout from './lib/components/EditorLayout.svelte';
  import VideoPreview from './lib/components/VideoPreview.svelte';
  import EditingPanel from './lib/components/EditingPanel.svelte';
  import Timeline from './lib/components/Timeline.svelte';
  import ExportModal from './lib/components/ExportModal.svelte';
  import './app.css';

  let jobId = null;
  let loading = true;
  let error = null;

  onMount(async () => {
    const pathSegments = window.location.pathname.split('/');
    const editIndex = pathSegments.indexOf('edit');
    if (editIndex > -1 && pathSegments.length > editIndex + 1) {
      jobId = pathSegments[editIndex + 1];
      await loadProject(jobId);
    } else {
      loading = false;
    }
  });

  async function loadProject(id) {
    try {
      loading = true;
      const response = await fetch(`/api/editor_data/${id}`);
      if (!response.ok) throw new Error('Failed to load project');
      const data = await response.json();
      
      currentProject.set({
        id: data.job_id,
        name: data.original_filename || 'Untitled',
        videoUrl: data.video_url,
        videoDuration: data.duration || 0,
        captions: data.captions || [],
        bRollClips: data.b_roll_clips || [],
        style: data.style || {},
        resolution: data.resolution || '1080x1920',
        createdAt: new Date(data.created_at),
        updatedAt: new Date(data.updated_at)
      });
      
      if (data.duration) {
        videoState.update(v => ({ ...v, duration: data.duration }));
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load project';
    } finally {
      loading = false;
    }
  }
</script>

<main class="h-screen w-full overflow-hidden bg-[#0a0a0a] text-white font-sans">
  {#if loading}
    <div class="flex items-center justify-center h-full">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
    </div>
  {:else if error}
    <div class="flex items-center justify-center h-full text-red-500">
      {error}
    </div>
  {:else if !$currentProject}
    <div class="flex flex-col items-center justify-center h-full text-gray-400 ml-16">
      <svg class="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      <p class="text-xl mb-2">No video selected</p>
      <p class="text-sm">Go to dashboard to select a video to edit</p>
      <a href="/" class="mt-4 px-4 py-2 bg-white text-black rounded-lg hover:bg-gray-200 transition">
        Go to Dashboard
      </a>
    </div>
  {:else}
    <EditorLayout>
      <Sidebar slot="sidebar" />
      <VideoPreview slot="preview" />
      <EditingPanel slot="panel" />
      <Timeline slot="timeline" />
    </EditorLayout>
  {/if}
</main>

<ExportModal />
