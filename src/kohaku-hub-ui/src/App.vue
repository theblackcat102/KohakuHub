<!-- src/kohaku-hub-ui/src/App.vue -->
<template>
  <div
    id="app"
    class="min-h-screen w-full bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors flex flex-col"
  >
    <TheHeader />
    <main class="flex-1 min-h-screen-content">
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
import TheHeader from "@/components/layout/TheHeader.vue";
import TheFooter from "@/components/layout/TheFooter.vue";

// Theme is applied early via inline script in index.html to prevent flash
// No need to initialize here

/**
 * Generate unique key for route to control when component should be reused
 * Same repo = same key = reuse component (no flicker)
 * Different repo = different key = new component instance
 */
function getRouteKey(route) {
  // Extract repo identifier from path
  const match = route.path.match(
    /^\/(models|datasets|spaces)\/([^/]+)\/([^/]+)/,
  );
  if (match) {
    const [, type, namespace, name] = match;
    return `${type}-${namespace}-${name}`;
  }
  return route.path;
}
</script>

<style scoped>
/* Prevent layout shift by ensuring main always has minimum height */
.min-h-screen-content {
  min-height: calc(100vh - 64px - 80px); /* viewport - header - footer approx */
}
</style>
