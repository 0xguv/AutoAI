import { writable } from 'svelte/store';

// Active tab store
export const activeTab = writable('captions');

// UI State
export const uiState = writable({
  isExporting: false,
  exportProgress: 0,
  selectedCaptionId: null,
  showPreview: true,
  sidebarOpen: true,
  activeWordIndex: -1
});