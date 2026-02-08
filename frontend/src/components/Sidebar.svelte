<script>
  import { Home, Settings, User, LogOut, Video } from 'lucide-svelte'
  
  function handleLogout() {
    window.location.href = '/logout'
  }
</script>

<aside class="fixed left-0 top-0 h-full w-16 bg-white border-r border-gray-200 flex flex-col items-center py-6 z-50 shadow-sm">
  <!-- Logo -->
  <div class="mb-8">
    <div class="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
      <Video class="w-6 h-6 text-white" />
    </div>
  </div>

  <!-- Navigation -->
  <nav class="flex-1 flex flex-col items-center space-y-2 w-full">
    <a 
      href="/" 
      class="w-12 h-12 rounded-xl bg-gray-100 text-gray-900 flex items-center justify-center hover:bg-gray-200 transition-colors"
      title="Home"
    >
      <Home class="w-5 h-5" />
    </a>
    
    <a 
      href="/editor-new" 
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-gray-100 hover:text-gray-900 transition-colors"
      title="New Editor"
    >
      <Video class="w-5 h-5" />
    </a>
    
    <a 
      href="/profile" 
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-gray-100 hover:text-gray-900 transition-colors"
      title="Profile"
    >
      <User class="w-5 h-5" />
    </a>
    
    <a 
      href="/" 
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-gray-100 hover:text-gray-900 transition-colors"
      title="Dashboard"
    >
      <Settings class="w-5 h-5" />
    </a>
  </nav>

  <!-- Bottom actions -->
  <div class="mt-auto w-full flex flex-col items-center space-y-2">
    <button 
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-red-50 hover:text-red-600 transition-colors"
      on:click={handleLogout}
      title="Logout"
    >
      <LogOut class="w-5 h-5" />
    </button>
  </div>
</aside>
