<script>
  import { onMount } from 'svelte';
  import { currentProject } from './lib/stores/projectStore';
  import { videoState } from './lib/stores/videoPlayerStore';
  import { uiState } from './lib/stores/uiStore';
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
      
      // Use captions directly from backend (word-level data)
      const captions = data.captions || [];
      const duration = captions.length > 0 && captions[captions.length - 1].words.length > 0
        ? captions[captions.length - 1].words[captions[captions.length - 1].words.length - 1].end
        : 0;
      
      currentProject.set({
        id: data.job_id,
        name: data.original_filename || 'Untitled',
        videoUrl: data.video_url,
        videoDuration: duration,
        captions: captions,
        bRollClips: [],
        style: {
          fontFamily: 'Inter',
          fontSize: 42,
          fontWeight: 'bold',
          color: '#FFFFFF',
          textShadow: 'medium',
          animation: 'pop',
          position: 'bottom',
          alignment: 'center',
          highlightWords: true,
          highlightColor: '#FFD700',
          wordByWord: true
        },
        resolution: data.resolution || '1080x1920',
        createdAt: new Date(),
        updatedAt: new Date()
      });
      
      if (duration) {
        videoState.update(v => ({ ...v, duration: duration }));
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load project';
    } finally {
      loading = false;
    }
  }
</script>

<main class="h-screen w-full overflow-hidden bg-dark text-dark-text font-sans">
  {#if loading}
    <div class="flex items-center justify-center h-full">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
    </div>
  {:else if error}
    <div class="flex items-center justify-center h-full text-red-500">
      {error}
    </div>
  {:else if !$currentProject}
    <div class="flex flex-col items-center justify-center h-full text-dark-text ml-16 px-8 text-center">
      <h2 class="text-5xl font-heading text-white mb-6 animate-fade-in">
        Start Creating Magic
      </h2>
      <p class="text-lg text-dark-text-light mb-8 max-w-xl animate-slide-up">
        Unleash the power of AI to transform your videos with stunning, viral-ready captions,
        emojis, and dynamic effects.
      </p>
      <div class="flex gap-4 mb-12 animate-bounce-in">
        <button 
          class="flex items-center gap-2 px-8 py-4 bg-primary text-white text-xl font-semibold rounded-xl shadow-lg hover:bg-primary-dark transition-all duration-300 transform hover:-translate-y-1"
          on:click={() => window.location.href = '/upload'}
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0l-4 4m4-4v12"/>
          </svg>
          Upload New Video
        </button>
        <a 
          href="/dashboard" 
          class="flex items-center gap-2 px-8 py-4 bg-dark-lighter text-dark-text-light text-xl font-semibold rounded-xl shadow-lg hover:bg-primary hover:text-white transition-all duration-300 transform hover:-translate-y-1"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
          Browse Projects
        </a>
      </div>
      <p class="text-sm text-dark-text mt-4">
        Need inspiration? Check out our <a href="/examples" class="text-primary hover:underline">examples gallery</a>.
      </p>
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
