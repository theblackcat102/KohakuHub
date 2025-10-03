<!-- src/components/common/MarkdownPage.vue -->
<template>
  <div class="container-main py-12">
    <article class="max-w-4xl mx-auto">
      <div class="card">
        <MarkdownViewer :content="content" />
      </div>
    </article>
  </div>
</template>

<script setup>
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

/**
 * @typedef {Object} Props
 * @property {string} content - Markdown content to render
 */
const props = defineProps({
  content: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
/* Additional styling for markdown pages */
.card :deep(.markdown-body) {
  max-width: none;
}

.card :deep(.markdown-body h1:first-child) {
  margin-top: 0;
}
</style>