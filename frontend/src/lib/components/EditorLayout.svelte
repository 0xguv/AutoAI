<script>
  import { uiState } from '../stores/uiStore';
</script>

<div class="flex h-screen w-full bg-dark">
  <!-- Left Sidebar Navigation -->
  <aside class="w-16 flex-shrink-0 border-r border-dark-lighter bg-dark-light">
    <slot name="sidebar" />
  </aside>

  <!-- Left Editing Panel (moved from right) -->
  <aside class="w-80 flex-shrink-0 border-r border-dark-lighter bg-dark-light overflow-y-auto">
    <slot name="panel" />
  </aside>

  <!-- Main Content Area -->
  <div class="flex-1 flex min-w-0">
    <!-- Center Workspace -->
    <div class="flex-1 flex flex-col min-w-0 bg-dark">
      <!-- Top Toolbar -->
      <header class="h-14 border-b border-dark-lighter flex items-center justify-between px-4 bg-dark-light">
        <div class="flex items-center gap-4">
          <h1 class="font-semibold text-lg text-dark-text-light">Video Editor</h1>
          <span class="text-xs text-dark-text">Auto-save enabled</span>
        </div>
        <div class="flex items-center gap-2">
          <button 
            class="px-4 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition flex items-center gap-2"
            on:click={() => uiState.update(u => ({ ...u, isExporting: true }))}
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            Export Video
          </button>
        </div>
      </header>

      <!-- Video Preview (Center) -->
      <div class="flex-1 flex items-center justify-center p-8 overflow-hidden">
        <slot name="preview" />
      </div>
    </div>

    <!-- Right Vertical Timeline -->
    <aside class="w-20 flex-shrink-0 border-l border-dark-lighter bg-dark-light">
      <slot name="timeline" />
    </aside>
  </div>
</div>
