<script>
  import { activeTab } from '../stores/uiStore';
  import { currentProject, STYLE_PRESETS } from '../stores/projectStore';
  import { aiContent } from '../stores/aiContentStore';
  import { Type, Palette, Film, Sparkles, Check, Loader2, Plus } from 'lucide-svelte';
  import { cn } from '../utils';

  let generatingAI = false;
  let searchQuery = '';
  let searchResults = [];
  let searching = false;

  const fonts = ['Inter', 'Poppins', 'Roboto', 'Oswald', 'Bebas Neue', 'Montserrat'];
  const positions = [
    { id: 'top', label: 'Top' },
    { id: 'middle', label: 'Middle' },
    { id: 'bottom', label: 'Bottom' }
  ];
  const animations = [
    { id: 'none', label: 'None' },
    { id: 'pop', label: 'Pop' },
    { id: 'slide-up', label: 'Slide Up' },
    { id: 'fade', label: 'Fade' },
    { id: 'bounce', label: 'Bounce' }
  ];

  async function generateAIContent() {
    if (!$currentProject) return;
    generatingAI = true;
    
    try {
      const transcript = $currentProject.captions.map(c => c.text).join(' ');
      const response = await fetch('/api/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript })
      });
      
      if (response.ok) {
        const data = await response.json();
        aiContent.set(data);
      }
    } catch (err) {
      console.error('AI generation failed:', err);
    } finally {
      generatingAI = false;
    }
  }

  async function searchBRoll() {
    if (!searchQuery) return;
    searching = true;
    
    try {
      const response = await fetch(`/api/broll/search?q=${encodeURIComponent(searchQuery)}`);
      if (response.ok) {
        const data = await response.json();
        searchResults = data.results || [];
      }
    } catch (err) {
      console.error('B-Roll search failed:', err);
    } finally {
      searching = false;
    }
  }

  function addBRollClip(clip) {
    if (!$currentProject) return;
    currentProject.addBRoll({
      id: crypto.randomUUID(),
      url: clip.video_url,
      thumbnail: clip.thumbnail,
      start: $currentProject.videoDuration * 0.3,
      duration: 5,
      source: clip.source
    });
  }
</script>

<div class="h-full flex flex-col bg-dark-light">
  <!-- Tab Content -->
  {#if $activeTab === 'captions'}
    <div class="p-4 space-y-4">
      <h3 class="font-semibold text-lg text-white">Caption Settings</h3>
      
      <div class="space-y-3">
        <label class="flex items-center justify-between p-3 bg-dark-lighter rounded-lg border border-dark-lighter cursor-pointer hover:border-primary transition">
          <span class="text-dark-text-light">Word-by-word highlighting</span>
          <input 
            type="checkbox" 
            checked={$currentProject?.style?.wordByWord}
            on:change={(e) => currentProject.updateStyle({ wordByWord: e.target.checked })}
            class="w-5 h-5 rounded border-dark-lighter text-primary focus:ring-primary"
          />
        </label>

        <label class="flex items-center justify-between p-3 bg-dark-lighter rounded-lg border border-dark-lighter cursor-pointer hover:border-primary transition">
          <span class="text-dark-text-light">Highlight active words</span>
          <input 
            type="checkbox" 
            checked={$currentProject?.style?.highlightWords}
            on:change={(e) => currentProject.updateStyle({ highlightWords: e.target.checked })}
            class="w-5 h-5 rounded border-dark-lighter text-primary focus:ring-primary"
          />
        </label>

        {#if $currentProject?.style?.highlightWords}
          <div class="space-y-2">
            <label class="text-sm text-dark-text-light">Highlight Color</label>
            <div class="flex gap-2">
              {#each ['#FFD700', '#FF6B6B', '#00F5FF', '#FF00FF', '#00FF00'] as color}
                <button
                  class="w-8 h-8 rounded-lg border-2 transition {($currentProject?.style?.highlightColor || '#FFD700') === color ? 'border-primary scale-110' : 'border-transparent hover:border-primary-light'}"
                  style="background-color: {color}"
                  on:click={() => currentProject.updateStyle({ highlightColor: color })}
                />
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>

  {:else if $activeTab === 'style'}
    <div class="p-4 space-y-6 overflow-y-auto">
      <div>
        <h3 class="font-semibold text-lg text-white mb-3">Style Presets</h3>
        <div class="grid grid-cols-2 gap-2">
          {#each Object.entries(STYLE_PRESETS) as [name, preset]}
            <button
              class="p-3 bg-dark-lighter rounded-lg border border-dark-lighter text-left hover:border-primary transition text-sm"
              on:click={() => currentProject.applyPreset(name)}
            >
              <div class="font-medium capitalize text-white">{name.replace('-', ' ')}</div>
              <div class="text-xs text-dark-text-light mt-1">
                {preset.fontWeight} • {preset.animation}
              </div>
            </button>
          {/each}
        </div>
      </div>

      <div class="space-y-4">
        <h3 class="font-semibold text-lg text-white">Typography</h3>
        
        <div class="space-y-2">
          <label class="text-sm text-dark-text-light">Font Family</label>
          <select 
            value={$currentProject?.style?.fontFamily || 'Inter'}
            on:change={(e) => currentProject.updateStyle({ fontFamily: e.target.value })}
            class="w-full p-2 bg-dark-lighter rounded-lg border border-dark-lighter text-white focus:border-primary focus:ring-1 focus:ring-primary"
          >
            {#each fonts as font}
              <option value={font}>{font}</option>
            {/each}
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-dark-text-light flex justify-between">
            <span>Font Size</span>
            <span class="text-white">{$currentProject?.style?.fontSize || 42}px</span>
          </label>
          <input 
            type="range" 
            min="20" 
            max="80" 
            value={$currentProject?.style?.fontSize || 42}
            on:input={(e) => currentProject.updateStyle({ fontSize: parseInt(e.target.value) })}
            class="w-full"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm text-dark-text-light">Position</label>
          <div class="flex gap-2">
            {#each positions as pos}
              <button
                class="flex-1 p-2 rounded-lg border text-sm transition {($currentProject?.style?.position || 'bottom') === pos.id ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter hover:border-primary'}"
                on:click={() => currentProject.updateStyle({ position: pos.id })}
              >
                {pos.label}
              </button>
            {/each}
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-dark-text-light">Animation</label>
          <select 
            value={$currentProject?.style?.animation || 'pop'}
            on:change={(e) => currentProject.updateStyle({ animation: e.target.value })}
            class="w-full p-2 bg-dark-lighter rounded-lg border border-dark-lighter text-white focus:border-primary focus:ring-1 focus:ring-primary"
          >
            {#each animations as anim}
              <option value={anim.id}>{anim.label}</option>
            {/each}
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-dark-text-light">Text Shadow</label>
          <div class="flex gap-2">
            {#each ['none', 'light', 'medium', 'heavy'] as shadow}
              <button
                class="flex-1 p-2 rounded-lg border text-sm transition {($currentProject?.style?.textShadow || 'medium') === shadow ? 'bg-primary text-white border-primary' : 'bg-dark-lighter text-dark-text-light border-dark-lighter hover:border-primary'}"
                on:click={() => currentProject.updateStyle({ textShadow: shadow })}
              >
                {shadow}
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>

  {:else if $activeTab === 'broll'}
    <div class="p-4 space-y-4">
      <h3 class="font-semibold text-lg text-white">B-Roll Library</h3>
      
      <div class="flex gap-2">
        <input 
          type="text" 
          bind:value={searchQuery}
          placeholder="Search stock footage..."
          class="flex-1 p-2 bg-dark-lighter rounded-lg border border-dark-lighter text-white placeholder-dark-text-light focus:border-primary focus:ring-1 focus:ring-primary"
          on:keydown={(e) => e.key === 'Enter' && searchBRoll()}
        />
        <button 
          on:click={searchBRoll}
          disabled={searching}
          class="p-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition disabled:opacity-50"
        >
          {#if searching}
            <Loader2 class="w-5 h-5 animate-spin" />
          {:else}
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
          {/if}
        </button>
      </div>

      {#if searchResults.length > 0}
        <div class="grid grid-cols-2 gap-2 max-h-96 overflow-y-auto">
          {#each searchResults as clip}
            <button
              class="relative aspect-video rounded-lg overflow-hidden group"
              on:click={() => addBRollClip(clip)}
            >
              <img src={clip.thumbnail} alt="" class="w-full h-full object-cover" />
              <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                <Plus class="w-8 h-8 text-white" />
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

  {:else if $activeTab === 'ai-tools'}
    <div class="p-4 space-y-4">
      <h3 class="font-semibold text-lg text-white">AI Magic Tools</h3>
      
      <button
        on:click={generateAIContent}
        disabled={generatingAI}
        class="w-full p-4 bg-gradient-to-r from-primary to-secondary rounded-lg font-medium text-white hover:from-primary-dark hover:to-secondary-dark transition disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {#if generatingAI}
          <Loader2 class="w-5 h-5 animate-spin" />
          Generating...
        {:else}
          <Sparkles class="w-5 h-5" />
          Generate Viral Content
        {/if}
      </button>

      {#if $aiContent}
        <div class="space-y-4">
          <div class="p-3 bg-dark-lighter rounded-lg border border-dark-lighter">
            <h4 class="font-medium text-sm text-dark-text-light mb-2">Hook Ideas</h4>
            <ul class="space-y-2">
              {#each $aiContent.hooks as hook}
                <li class="text-sm p-2 bg-dark rounded text-white">{hook}</li>
              {/each}
            </ul>
          </div>

          <div class="p-3 bg-dark-lighter rounded-lg border border-dark-lighter">
            <h4 class="font-medium text-sm text-dark-text-light mb-2">Description</h4>
            <p class="text-sm text-white">{$aiContent.descriptions[0]}</p>
          </div>

          <div class="p-3 bg-dark-lighter rounded-lg border border-dark-lighter">
            <h4 class="font-medium text-sm text-dark-text-light mb-2">Hashtags</h4>
            <p class="text-sm text-primary">{$aiContent.hashtags.join(' ')}</p>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
