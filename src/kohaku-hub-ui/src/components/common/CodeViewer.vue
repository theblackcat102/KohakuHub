<!-- src/components/common/CodeViewer.vue -->
<template>
  <div class="code-viewer">
    <div
      class="flex items-center justify-between mb-3 pb-3 border-b border-gray-200 dark:border-gray-700"
    >
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <el-tag size="small" type="info">{{ language }}</el-tag>
        <span
          class="text-xs sm:text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap"
          >{{ lineCount }} lines</span
        >
      </div>
      <el-button size="small" @click="copyCode" class="flex-shrink-0">
        <div class="i-carbon-copy inline-block mr-1" />
        <span class="hidden sm:inline">Copy</span>
        <span class="sm:hidden">Copy</span>
      </el-button>
    </div>

    <div class="code-container" v-html="highlightedCode" />
  </div>
</template>

<script setup>
import hljs from "highlight.js/lib/core";
import { ElMessage } from "element-plus";
import { ref, computed, watch, onMounted } from "vue";

// Import languages (same as markdown.js)
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import java from "highlight.js/lib/languages/java";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import go from "highlight.js/lib/languages/go";
import rust from "highlight.js/lib/languages/rust";
import php from "highlight.js/lib/languages/php";
import ruby from "highlight.js/lib/languages/ruby";
import swift from "highlight.js/lib/languages/swift";
import kotlin from "highlight.js/lib/languages/kotlin";
import shell from "highlight.js/lib/languages/shell";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";
import markdown from "highlight.js/lib/languages/markdown";
import css from "highlight.js/lib/languages/css";
import sql from "highlight.js/lib/languages/sql";

// Register languages
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("js", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("ts", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("py", python);
hljs.registerLanguage("java", java);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("csharp", csharp);
hljs.registerLanguage("cs", csharp);
hljs.registerLanguage("go", go);
hljs.registerLanguage("rust", rust);
hljs.registerLanguage("rs", rust);
hljs.registerLanguage("php", php);
hljs.registerLanguage("ruby", ruby);
hljs.registerLanguage("rb", ruby);
hljs.registerLanguage("swift", swift);
hljs.registerLanguage("kotlin", kotlin);
hljs.registerLanguage("kt", kotlin);
hljs.registerLanguage("shell", shell);
hljs.registerLanguage("sh", shell);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("yml", yaml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("md", markdown);
hljs.registerLanguage("css", css);
hljs.registerLanguage("sql", sql);

const props = defineProps({
  code: {
    type: String,
    required: true,
  },
  language: {
    type: String,
    default: "text",
  },
});

const highlightedCode = ref("");

const lineCount = computed(() => {
  return props.code ? props.code.split("\n").length : 0;
});

function highlightCode() {
  try {
    const lang = props.language || "text";

    if (hljs.getLanguage(lang)) {
      const result = hljs.highlight(props.code, { language: lang });
      highlightedCode.value = `<pre><code class="hljs language-${lang}">${result.value}</code></pre>`;
    } else {
      // Fallback to plain text
      highlightedCode.value = `<pre><code class="hljs">${escapeHtml(props.code)}</code></pre>`;
    }
  } catch (error) {
    console.error("Failed to highlight code:", error);
    highlightedCode.value = `<pre><code class="hljs">${escapeHtml(props.code)}</code></pre>`;
  }
}

function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function copyCode() {
  navigator.clipboard.writeText(props.code);
  ElMessage.success("Code copied to clipboard");
}

// Watch for code or language changes
watch([() => props.code, () => props.language], highlightCode, {
  immediate: true,
});

onMounted(() => {
  highlightCode();
});
</script>

<style scoped>
.code-viewer {
  width: 100%;
}

.code-container {
  overflow-x: auto;
  border-radius: 6px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
}

.dark .code-container {
  background-color: #0d1117;
  border-color: #30363d;
}

.code-container :deep(pre) {
  margin: 0;
  padding: 16px;
  background-color: #ffffff !important;
  border-radius: 6px;
}

.dark .code-container :deep(pre) {
  background-color: #0d1117 !important;
}

.code-container :deep(code) {
  font-family:
    ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono",
    monospace;
  font-size: 11px;
  line-height: 1.5;
  background: transparent !important;
  padding: 0 !important;
  color: #24292f;
}

@media (min-width: 640px) {
  .code-container :deep(code) {
    font-size: 12px;
  }
}

@media (min-width: 768px) {
  .code-container :deep(code) {
    font-size: 14px;
  }
}

.dark .code-container :deep(code) {
  color: #c9d1d9;
}

.code-container :deep(.hljs) {
  background: transparent !important;
  padding: 0 !important;
  color: #24292f;
}

.dark .code-container :deep(.hljs) {
  color: #c9d1d9;
}

/* Override highlight.js colors for light mode */
.code-container :deep(.hljs-keyword),
.code-container :deep(.hljs-selector-tag),
.code-container :deep(.hljs-literal),
.code-container :deep(.hljs-section),
.code-container :deep(.hljs-link) {
  color: #cf222e;
}

.code-container :deep(.hljs-function),
.code-container :deep(.hljs-params) {
  color: #8250df;
}

.code-container :deep(.hljs-string),
.code-container :deep(.hljs-bullet),
.code-container :deep(.hljs-title) {
  color: #0a3069;
}

.code-container :deep(.hljs-comment),
.code-container :deep(.hljs-quote) {
  color: #6e7781;
  font-style: italic;
}

.code-container :deep(.hljs-number),
.code-container :deep(.hljs-regexp),
.code-container :deep(.hljs-tag) {
  color: #0550ae;
}

.code-container :deep(.hljs-attr),
.code-container :deep(.hljs-variable),
.code-container :deep(.hljs-template-variable),
.code-container :deep(.hljs-attribute) {
  color: #953800;
}

/* Dark mode colors - keep default highlight.js github-dark theme */
.dark .code-container :deep(.hljs-keyword),
.dark .code-container :deep(.hljs-selector-tag),
.dark .code-container :deep(.hljs-literal) {
  color: #ff7b72;
}

.dark .code-container :deep(.hljs-function) {
  color: #d2a8ff;
}

.dark .code-container :deep(.hljs-string) {
  color: #a5d6ff;
}

.dark .code-container :deep(.hljs-comment) {
  color: #8b949e;
}

.dark .code-container :deep(.hljs-number) {
  color: #79c0ff;
}

.dark .code-container :deep(.hljs-attr),
.dark .code-container :deep(.hljs-variable),
.dark .code-container :deep(.hljs-template-variable),
.dark .code-container :deep(.hljs-attribute) {
  color: #79c0ff; /* Brighter blue for JSON keys in dark mode */
}

/* Line numbers */
.code-container :deep(.line) {
  display: inline-block;
  min-height: 1.5em;
}
</style>
