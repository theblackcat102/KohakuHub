<!-- src/kohaku-hub-ui/src/components/layout/TheFooter.vue -->
<template>
  <footer class="bg-gray-100 border-t border-gray-200 mt-4">
    <div class="container-main py-8">
      <div class="grid grid-cols-4 gap-8">
        <div>
          <h3 class="font-semibold mb-3">KohakuHub</h3>
          <p class="text-sm text-gray-600">
            Self-hosted HuggingFace Hub alternative
          </p>
        </div>
        
        <div>
          <h3 class="font-semibold mb-3">Resources</h3>
          <div class="flex flex-col gap-2 text-sm">
            <a href="/docs" class="text-gray-600 hover:text-blue-500">Documentation</a>
            <a href="/about" class="text-gray-600 hover:text-blue-500">About</a>
          </div>
        </div>
        
        <div>
          <h3 class="font-semibold mb-3">Community</h3>
          <div class="flex flex-col gap-2 text-sm">
            <a href="https://github.com/KohakuBlueleaf/KohakuHub" target="_blank" class="text-gray-600 hover:text-blue-500">
              GitHub
            </a>
            <a href="https://discord.gg/xWYrkyvJ2s" target="_blank" class="text-gray-600 hover:text-blue-500">
              Discord
            </a>
          </div>
        </div>
        
        <div>
          <h3 class="font-semibold mb-3">Legal</h3>
          <div class="flex flex-col gap-2 text-sm">
            <a href="/terms" class="text-gray-600 hover:text-blue-500">Terms</a>
            <a href="/privacy" class="text-gray-600 hover:text-blue-500">Privacy</a>
          </div>
        </div>
      </div>
      
      <div class="mt-8 pt-8 border-t border-gray-300 text-center text-sm text-gray-600">
        © 2025 KohakuHub. Licensed under AGPL-3.0
      </div>
    </div>
  </footer>
</template>