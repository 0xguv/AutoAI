<script>
  import { Clock, Trash2, Copy, GripVertical } from 'lucide-svelte'
  
  export let captions = []
  export let currentTime = 0
  export let onUpdate
  export let onCaptionClick
  
  let editingId = null
  let editText = ''
  
  function startEdit(caption) {
    editingId = caption.id
    editText = caption.text
  }
  
  function saveEdit(id) {
    if (onUpdate) {
      onUpdate(id, editText)
    }
    editingId = null
  }
  
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 100)
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
  }
  
  function deleteCaption(id) {
    captions = captions.filter(c => c.id !== id)
  }
  
  function duplicateCaption(caption) {
    const newCaption = {
      ...caption,
      id: Date.now(),
      start: caption.end,
      end: caption.end + (caption.end - caption.start)
    }
    const index = captions.findIndex(c => c.id === caption.id)
    captions = [...captions.slice(0, index + 1), newCaption, ...captions.slice(index + 1)]
  }
</script>

<aside class="w-96 bg-white border-l border-gray-200 flex flex-col">
  <!-- Panel Header -->
  <div class="px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50">
    <div class="flex items-center space-x-2">
      <Clock class="w-4 h-4 text-gray-500" />
      <h2 class="font-semibold text-gray-900">Timeline</h2>
    </div>
    <span class="text-sm text-gray-500">{captions.length} captions</span>
  </div>
  
  <!-- Caption List -->
  <div class="flex-1 overflow-y-auto p-4 space-y-3">
    {#each captions as caption (caption.id)}
      <div 
        class="group relative bg-white border-2 rounded-xl p-4 transition-all hover:shadow-md cursor-pointer"
        class:border-green-500={caption.active}
        class:border-gray-200={!caption.active}
        class:bg-green-50={caption.active}
        on:click={() => onCaptionClick && onCaptionClick(caption)}
      >
        <!-- Drag Handle -->
        <div class="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-300 cursor-grab active:cursor-grabbing">
          <GripVertical class="w-4 h-4" />
        </div>
        
        <div class="pl-6">
          <!-- Time Range -->
          <div class="flex items-center space-x-2 text-xs text-gray-500 mb-2">
            <span class="font-mono bg-gray-100 px-2 py-0.5 rounded">{formatTime(caption.start)}</span>
            <span>→</span>
            <span class="font-mono bg-gray-100 px-2 py-0.5 rounded">{formatTime(caption.end)}</span>
            <span class="text-gray-400">({(caption.end - caption.start).toFixed(1)}s)</span>
          </div>
          
          <!-- Caption Text -->
          {#if editingId === caption.id}
            <textarea
              class="w-full text-sm border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
              rows="2"
              bind:value={editText}
              on:blur={() => saveEdit(caption.id)}
              on:keydown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), saveEdit(caption.id))}
              autofocus
            />
          {:else}
            <p 
              class="text-sm text-gray-800 leading-relaxed cursor-text"
              on:click|stopPropagation={() => startEdit(caption)}
            >
              {caption.text}
            </p>
          {/if}
        </div>
        
        <!-- Actions -->
        <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1">
          <button 
            class="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded transition-colors"
            on:click|stopPropagation={() => duplicateCaption(caption)}
            title="Duplicate"
          >
            <Copy class="w-4 h-4" />
          </button>
          <button 
            class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
            on:click|stopPropagation={() => deleteCaption(caption.id)}
            title="Delete"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
        
        <!-- Progress indicator -->
        {#if currentTime >= caption.start && currentTime <= caption.end}
          <div class="absolute bottom-0 left-0 right-0 h-1 bg-green-500 rounded-b-xl">
            <div 
              class="h-full bg-green-600 rounded-full transition-all"
              style="width: {((currentTime - caption.start) / (caption.end - caption.start)) * 100}%"
            ></div>
          </div>
        {/if}
      </div>
    {/each}
  </div>
  
  <!-- Add Caption Button -->
  <div class="p-4 border-t border-gray-200 bg-gray-50">
    <button 
      class="w-full py-2.5 bg-gray-900 text-white rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors flex items-center justify-center space-x-2"
      on:click={() => {
        const lastCaption = captions[captions.length - 1]
        const newCaption = {
          id: Date.now(),
          text: "New caption",
          start: lastCaption ? lastCaption.end : 0,
          end: lastCaption ? lastCaption.end + 3 : 3,
          active: false
        }
        captions = [...captions, newCaption]
      }}
    >
      <span>+ Add Caption</span>
    </button>
  </div>
</aside>
