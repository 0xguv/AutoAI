<script>
  import { activeTab, currentProject } from '../stores/editor';
  import { Type, Palette, Film, Sparkles } from 'lucide-svelte';

  const tabs = [
    { id: 'captions', label: 'Captions', icon: Type },
    { id: 'style', label: 'Style', icon: Palette },
    { id: 'broll', label: 'B-Roll', icon: Film },
    { id: 'ai-tools', label: 'AI Tools', icon: Sparkles }
  ];

  function handleLogout() {
    window.location.href = '/logout';
  }
</script>

<div class="flex flex-col h-full">
  <!-- Logo -->
  <div class="h-14 flex items-center justify-center border-b border-white/10">
    <a href="/" class="text-white">
      <svg class="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v12"/>
        <path d="M9 9h6v6H9z"/>
      </svg>
    </a>
  </div>

  <!-- Navigation Tabs -->
  <nav class="flex-1 flex flex-col items-center py-4 gap-1">
    {#each tabs as tab}
      <button
        class="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 group relative {$activeTab === tab.id ? 'bg-white text-black' : 'text-gray-400 hover:text-white hover:bg-white/10'}"
        on:click={() => activeTab.set(tab.id)}
        title={tab.label}
      >
        <svelte:component this={tab.icon} class="w-5 h-5" />
        
        <!-- Tooltip -->
        <span class="absolute left-14 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition pointer-events-none whitespace-nowrap z-50">
          {tab.label}
        </span>
      </button>
    {/each}
  </nav>

  <!-- Bottom Actions -->
  <div class="flex flex-col items-center py-4 gap-2 border-t border-white/10">
    <a 
      href="/profile"
      class="w-12 h-12 rounded-xl text-gray-400 flex items-center justify-center hover:text-white hover:bg-white/10 transition"
      title="Profile"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
      </svg>
    </a>
    
    <button 
      class="w-12 h-12 rounded-xl text-gray-400 flex items-center justify-center hover:text-red-400 hover:bg-red-400/10 transition"
      on:click={handleLogout}
      title="Logout"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
      </svg>
    </button>
  </div>
</div>
