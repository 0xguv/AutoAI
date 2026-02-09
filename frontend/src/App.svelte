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

  // Parse SRT content to caption format
  function parseSRT(srtContent) {
    if (!srtContent) return [];
    
    const captions = [];
    const blocks = srtContent.trim().split(/\n\s*\n/);
    
    blocks.forEach((block, index) => {
      const lines = block.trim().split('\n');
      if (lines.length < 3) return;
      
      // Parse time line (e.g., "00:00:01,000 --> 00:00:04,000")
      const timeLine = lines[1];
      const timeMatch = timeLine.match(/(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})/);
      
      if (timeMatch) {
        const start = parseTime(timeMatch[1]);
        const end = parseTime(timeMatch[2]);
        const text = lines.slice(2).join(' ').trim();
        
        // Split text into words with estimated timestamps
        const words = text.split(' ').map((word, wordIndex) => {
          const wordDuration = (end - start) / text.split(' ').length;
          return {
            text: word,
            start: start + (wordIndex * wordDuration),
            end: start + ((wordIndex + 1) * wordDuration),
            confidence: 0.95
          };
        });
        
        captions.push({
          id: `caption_${index}`,
          text: text,
          start: start,
          end: end,
          words: words
        });
      }
    });
    
    return captions;
  }
  
  function parseTime(timeStr) {
    // Convert "00:00:01,000" to seconds
    const parts = timeStr.match(/(\d{2}):(\d{2}):(\d{2}),(\d{3})/);
    if (!parts) return 0;
    
    const hours = parseInt(parts[1]);
    const minutes = parseInt(parts[2]);
    const seconds = parseInt(parts[3]);
    const milliseconds = parseInt(parts[4]);
    
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
  }

  async function loadProject(id) {
    try {
      loading = true;
      const response = await fetch(`/api/editor_data/${id}`);
      if (!response.ok) throw new Error('Failed to load project');
      const data = await response.json();
      
      // Parse SRT content to structured captions
      const captions = parseSRT(data.srt_content);
      const duration = captions.length > 0 ? captions[captions.length - 1].end : 0;
      
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

<main class="h-screen w-full overflow-hidden bg-white text-gray-900 font-sans">
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
