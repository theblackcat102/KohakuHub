<!-- src/kohaku-hub-ui/src/App.vue -->
<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <TheHeader />
    <main>
      <RouterView v-slot="{ Component, route }">
        <keep-alive :include="['RepoViewer']">
          <component :is="Component" :key="getRouteKey(route)" />
        </keep-alive>
      </RouterView>
    </main>
    <TheFooter />
  </div>
</template>

<script setup>
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'

/**
 * Generate unique key for route to control when component should be reused
 * Same repo = same key = reuse component (no flicker)
 * Different repo = different key = new component instance
 */
function getRouteKey(route) {
  // Extract repo identifier from path
  const match = route.path.match(/^\/(models|datasets|spaces)\/([^/]+)\/([^/]+)/)
  if (match) {
    const [, type, namespace, name] = match
    return `${type}-${namespace}-${name}`
  }
  return route.path
}
</script>