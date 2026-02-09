<script>
  import { Home, User, LogOut } from 'lucide-svelte'
  
  function handleLogout() {
    window.location.href = '/logout'
  }
</script>

<aside class="fixed left-0 top-0 h-full w-16 bg-white border-r border-gray-200 flex flex-col items-center py-6 z-50">
  <!-- Logo - redirects to home -->
  <div class="mb-8">
    <a href="/" class="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center hover:bg-gray-800 transition-colors">
      <!-- Coin Icon -->
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white"><circle cx="12" cy="12" r="10"/><path d="M12 6v12"/><path d="M9 9h6v6H9z"/></svg>
    </a>
  </div>

  <!-- Navigation -->
  <nav class="flex-1 flex flex-col items-center space-y-2 w-full">
    <a 
      href="/" 
      class="w-12 h-12 rounded-xl bg-gray-100 text-gray-900 flex items-center justify-center hover:bg-gray-200 transition-colors"
      title="Home"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    </a>
  </nav>

  <!-- Bottom actions -->
  <div class="mt-auto w-full flex flex-col items-center space-y-2 pb-2">
    <!-- Token Indicator (simplified) -->
    <div class="mb-2">
      <div class="flex items-center justify-center px-2 py-1.5 bg-gray-100 rounded-lg border border-gray-200 cursor-default" title="Tokens">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-600 mr-1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v12"/><path d="M8 10h8v4H8z"/></svg>
        <span class="text-sm font-semibold text-gray-700">-</span>
      </div>
    </div>
    
    <a 
      href="/profile"
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-gray-100 hover:text-gray-900 transition-colors"
      title="Profile"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
    </a>
    
    <a 
      href="/logout"
      class="w-12 h-12 rounded-xl text-gray-500 flex items-center justify-center hover:bg-red-50 hover:text-red-600 transition-colors"
      title="Logout"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
    </a>
  </div>
</aside>
