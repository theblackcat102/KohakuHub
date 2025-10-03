<!-- src/kohaku-hub-ui/src/App.vue -->
<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <TheHeader />
    <main>
      <RouterView />
    </main>
    <TheFooter />
  </div>
</template>

<script setup>
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
</script>