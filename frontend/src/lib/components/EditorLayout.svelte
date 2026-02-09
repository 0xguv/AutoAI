<script>
  import { uiState } from '../stores/editor';
</script>

<div class="flex h-screen w-full bg-white">
  <!-- Left Sidebar Navigation -->
  <aside class="w-16 flex-shrink-0 border-r border-gray-200 bg-gray-50">
    <slot name="sidebar" />
  </aside>

  <!-- Main Content Area -->
  <div class="flex-1 flex flex-col min-w-0">
    <!-- Top Toolbar -->
    <header class="h-14 border-b border-gray-200 flex items-center justify-between px-4 bg-white">
      <div class="flex items-center gap-4">
        <h1 class="font-semibold text-lg text-gray-900">Video Editor</h1>
        <span class="text-xs text-gray-400">Auto-save enabled</span>
      </div>
      <div class="flex items-center gap-2">
        <button 
          class="px-4 py-2 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 transition flex items-center gap-2"
          on:click={() => uiState.update(u => ({ ...u, isExporting: true }))}
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Export Video
        </button>
      </div>
    </header>

    <!-- Center Workspace -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Video Preview (Center) -->
      <div class="flex-1 flex flex-col min-w-0 bg-gray-100">
        <div class="flex-1 flex items-center justify-center p-8 overflow-hidden">
          <slot name="preview" />
        </div>
        
        <!-- Timeline (Bottom of center) -->
        <div class="h-48 border-t border-gray-200 bg-white">
          <slot name="timeline" />
        </div>
      </div>

      <!-- Right Editing Panel -->
      <aside class="w-80 flex-shrink-0 border-l border-gray-200 bg-gray-50 overflow-y-auto">
        <slot name="panel" />
      </aside>
    </div>
  </div>
</div>
