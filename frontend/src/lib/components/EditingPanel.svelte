<script>
  import { activeTab, currentProject, STYLE_PRESETS, aiContent } from '../stores/editor';
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

<div class="h-full flex flex-col">
  <!-- Tab Content -->
  {#if $activeTab === 'captions'}
    <div class="p-4 space-y-4">
      <h3 class="font-semibold text-lg">Caption Settings</h3>
      
      <div class="space-y-3">
        <label class="flex items-center justify-between p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition">
          <span>Word-by-word highlighting</span>
          <input 
            type="checkbox" 
            checked={$currentProject?.style?.wordByWord}
            on:change={(e) => currentProject.updateStyle({ wordByWord: e.target.checked })}
            class="w-5 h-5 rounded border-gray-600 text-blue-500 focus:ring-blue-500"
          />
        </label>

        <label class="flex items-center justify-between p-3 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition">
          <span>Highlight active words</span>
          <input 
            type="checkbox" 
            checked={$currentProject?.style?.highlightWords}
            on:change={(e) => currentProject.updateStyle({ highlightWords: e.target.checked })}
            class="w-5 h-5 rounded border-gray-600 text-blue-500 focus:ring-blue-500"
          />
        </label>

        {#if $currentProject?.style?.highlightWords}
          <div class="space-y-2">
            <label class="text-sm text-gray-400">Highlight Color</label>
            <div class="flex gap-2">
              {#each ['#FFD700', '#FF6B6B', '#00F5FF', '#FF00FF', '#00FF00'] as color}
                <button
                  class="w-8 h-8 rounded-lg border-2 transition {($currentProject?.style?.highlightColor || '#FFD700') === color ? 'border-white scale-110' : 'border-transparent hover:border-white/50'}"
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
        <h3 class="font-semibold text-lg mb-3">Style Presets</h3>
        <div class="grid grid-cols-2 gap-2">
          {#each Object.entries(STYLE_PRESETS) as [name, preset]}
            <button
              class="p-3 bg-white/5 rounded-lg text-left hover:bg-white/10 transition text-sm"
              on:click={() => currentProject.applyPreset(name)}
            >
              <div class="font-medium capitalize">{name.replace('-', ' ')}</div>
              <div class="text-xs text-gray-500 mt-1">
                {preset.fontWeight} • {preset.animation}
              </div>
            </button>
          {/each}
        </div>
      </div>

      <div class="space-y-4">
        <h3 class="font-semibold text-lg">Typography</h3>
        
        <div class="space-y-2">
          <label class="text-sm text-gray-400">Font Family</label>
          <select 
            value={$currentProject?.style?.fontFamily || 'Inter'}
            on:change={(e) => currentProject.updateStyle({ fontFamily: e.target.value })}
            class="w-full p-2 bg-white/5 rounded-lg border border-white/10 text-white"
          >
            {#each fonts as font}
              <option value={font}>{font}</option>
            {/each}
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-gray-400 flex justify-between">
            <span>Font Size</span>
            <span>{$currentProject?.style?.fontSize || 42}px</span>
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
          <label class="text-sm text-gray-400">Position</label>
          <div class="flex gap-2">
            {#each positions as pos}
              <button
                class="flex-1 p-2 bg-white/5 rounded-lg text-sm transition {($currentProject?.style?.position || 'bottom') === pos.id ? 'bg-white text-black' : 'hover:bg-white/10'}"
                on:click={() => currentProject.updateStyle({ position: pos.id })}
              >
                {pos.label}
              </button>
            {/each}
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-gray-400">Animation</label>
          <select 
            value={$currentProject?.style?.animation || 'pop'}
            on:change={(e) => currentProject.updateStyle({ animation: e.target.value })}
            class="w-full p-2 bg-white/5 rounded-lg border border-white/10 text-white"
          >
            {#each animations as anim}
              <option value={anim.id}>{anim.label}</option>
            {/each}
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm text-gray-400">Text Shadow</label>
          <div class="flex gap-2">
            {#each ['none', 'light', 'medium', 'heavy'] as shadow}
              <button
                class="flex-1 p-2 bg-white/5 rounded-lg text-sm transition {($currentProject?.style?.textShadow || 'medium') === shadow ? 'bg-white text-black' : 'hover:bg-white/10'}"
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
      <h3 class="font-semibold text-lg">B-Roll Library</h3>
      
      <div class="flex gap-2">
        <input 
          type="text" 
          bind:value={searchQuery}
          placeholder="Search stock footage..."
          class="flex-1 p-2 bg-white/5 rounded-lg border border-white/10 text-white placeholder-gray-500"
          on:keydown={(e) => e.key === 'Enter' && searchBRoll()}
        />
        <button 
          on:click={searchBRoll}
          disabled={searching}
          class="p-2 bg-white text-black rounded-lg hover:bg-gray-200 transition disabled:opacity-50"
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
      <h3 class="font-semibold text-lg">AI Magic Tools</h3>
      
      <button
        on:click={generateAIContent}
        disabled={generatingAI}
        class="w-full p-4 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
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
          <div class="p-3 bg-white/5 rounded-lg">
            <h4 class="font-medium text-sm text-gray-400 mb-2">Hook Ideas</h4>
            <ul class="space-y-2">
              {#each $aiContent.hooks as hook}
                <li class="text-sm p-2 bg-white/5 rounded">{hook}</li>
              {/each}
            </ul>
          </div>

          <div class="p-3 bg-white/5 rounded-lg">
            <h4 class="font-medium text-sm text-gray-400 mb-2">Description</h4>
            <p class="text-sm">{$aiContent.descriptions[0]}</p>
          </div>

          <div class="p-3 bg-white/5 rounded-lg">
            <h4 class="font-medium text-sm text-gray-400 mb-2">Hashtags</h4>
            <p class="text-sm text-blue-400">{$aiContent.hashtags.join(' ')}</p>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
