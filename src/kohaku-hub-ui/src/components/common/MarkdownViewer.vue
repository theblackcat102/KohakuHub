<!-- src/kohaku-hub-ui/src/components/common/MarkdownViewer.vue -->
<template>
  <div class="markdown-body markdown-container" v-html="renderedHTML" />
</template>

<script setup>
import { renderMarkdown } from "@/utils/markdown";

/**
 * @typedef {Object} Props
 * @property {string} content - Markdown content to render
 * @property {boolean} stripFrontmatter - Strip YAML frontmatter (default: true for repo cards)
 */
const props = defineProps({
  content: {
    type: String,
    default: "",
  },
  stripFrontmatter: {
    type: Boolean,
    default: true,
  },
});

const renderedHTML = computed(() => {
  return renderMarkdown(props.content, {
    stripFrontmatter: props.stripFrontmatter,
  });
});
</script>

<style scoped>
/* Strict containment for markdown content */
.markdown-container {
  /* Prevent overflow but don't break layout */
  max-width: 100%;
  overflow-x: auto;
}

/* GitHub-like markdown styles */
.markdown-body {
  font-size: 16px;
  line-height: 1.6;
  word-wrap: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.25em;
}

.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-body :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
  font-family: ui-monospace, monospace;
}

.markdown-body :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.markdown-body :deep(pre code) {
  display: inline;
  max-width: auto;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body :deep(a) {
  color: #0969da;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 2em;
  margin-bottom: 16px;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25em;
}

.markdown-body :deep(blockquote) {
  padding: 0 1em;
  color: #57606a;
  border-left: 0.25em solid #d0d7de;
  margin-bottom: 16px;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 16px;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #d0d7de;
}

.markdown-body :deep(table th) {
  font-weight: 600;
  background-color: #f6f8fa;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.markdown-body :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #d0d7de;
  border: 0;
}

/* Ensure all custom content stays within bounds */
.markdown-body :deep(*) {
  max-width: 100%;
  box-sizing: border-box;
}

/* Allow radio inputs for galleries but keep them functional */
.markdown-body :deep(input[type="radio"]) {
  /* Radio inputs can be visible or hidden based on custom styles */
  pointer-events: auto;
}

/* Ensure custom containers don't overflow */
.markdown-body :deep(div),
.markdown-body :deep(section),
.markdown-body :deep(article) {
  max-width: 100%;
  overflow-x: auto;
}

/* Fix for gallery containers that use position: relative */
.markdown-body :deep(.gallery-container),
.markdown-body :deep([class*="gallery"]) {
  max-width: 100%;
  overflow: hidden;
}

/* Ensure slides and content areas stay contained */
.markdown-body :deep(.content-area),
.markdown-body :deep(.slide) {
  max-width: 100%;
  box-sizing: border-box;
}

/* Dark mode support for markdown elements */
.markdown-body :deep(h1),
.markdown-body :deep(h2) {
  border-bottom-color: #eaecef;
}

@media (prefers-color-scheme: dark) {
  .markdown-body :deep(h1),
  .markdown-body :deep(h2) {
    border-bottom-color: rgba(255, 255, 255, 0.1);
  }

  .markdown-body :deep(pre) {
    background-color: rgba(0, 0, 0, 0.2);
  }

  .markdown-body :deep(code) {
    background-color: rgba(255, 255, 255, 0.1);
  }

  .markdown-body :deep(table th) {
    background-color: rgba(0, 0, 0, 0.2);
  }

  .markdown-body :deep(table th),
  .markdown-body :deep(table td) {
    border-color: rgba(255, 255, 255, 0.1);
  }

  .markdown-body :deep(blockquote) {
    color: #8b949e;
    border-left-color: rgba(255, 255, 255, 0.2);
  }
}

/* Handle dark mode class from theme store */
:global(.dark) .markdown-body :deep(h1),
:global(.dark) .markdown-body :deep(h2) {
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

:global(.dark) .markdown-body :deep(pre) {
  background-color: rgba(0, 0, 0, 0.3);
}

:global(.dark) .markdown-body :deep(code) {
  background-color: rgba(255, 255, 255, 0.1);
}

:global(.dark) .markdown-body :deep(table th) {
  background-color: rgba(0, 0, 0, 0.3);
}

:global(.dark) .markdown-body :deep(table th),
:global(.dark) .markdown-body :deep(table td) {
  border-color: rgba(255, 255, 255, 0.1);
}

:global(.dark) .markdown-body :deep(blockquote) {
  color: #8b949e;
  border-left-color: rgba(255, 255, 255, 0.2);
}

:global(.dark) .markdown-body :deep(a) {
  color: #58a6ff;
}
</style>
