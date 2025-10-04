<!-- src/components/common/CodeEditor.vue -->
<template>
  <div class="code-editor-wrapper">
    <div class="editor-toolbar">
      <div class="flex items-center gap-2">
        <el-tag size="small" type="info">{{ language }}</el-tag>
        <span class="text-sm text-gray-600 dark:text-gray-400">
          {{ lineCount }} lines
        </span>
        <span v-if="modified" class="text-xs text-orange-500">● Modified</span>
      </div>
      <div class="flex items-center gap-2">
        <el-button v-if="modified" size="small" @click="resetContent">
          <div class="i-carbon-reset inline-block mr-1" />
          Reset
        </el-button>
        <el-button
          size="small"
          type="primary"
          :disabled="!modified || saving"
          :loading="saving"
          @click="saveFile"
        >
          <div v-if="!saving" class="i-carbon-save inline-block mr-1" />
          {{ saving ? "Saving..." : "Save" }}
        </el-button>
      </div>
    </div>
    <div ref="editorContainer" class="editor-container" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { keymap } from "@codemirror/view";
import { defaultKeymap, indentWithTab } from "@codemirror/commands";
import { oneDark } from "@codemirror/theme-one-dark";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { rust } from "@codemirror/lang-rust";
import { php } from "@codemirror/lang-php";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { xml } from "@codemirror/lang-xml";
import { sql } from "@codemirror/lang-sql";
import { ElMessage } from "element-plus";

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  language: {
    type: String,
    default: "plaintext",
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
  height: {
    type: String,
    default: "600px",
  },
});

const emit = defineEmits(["update:modelValue", "save", "change"]);

const editorContainer = ref(null);
const editor = ref(null);
const originalContent = ref(props.modelValue);
const currentContent = ref(props.modelValue);
const saving = ref(false);

const modified = computed(() => {
  return currentContent.value !== originalContent.value;
});

const lineCount = computed(() => {
  return currentContent.value ? currentContent.value.split("\n").length : 0;
});

function getLanguageExtension(lang) {
  const langMap = {
    javascript: javascript(),
    js: javascript(),
    jsx: javascript({ jsx: true }),
    typescript: javascript({ typescript: true }),
    ts: javascript({ typescript: true }),
    tsx: javascript({ typescript: true, jsx: true }),
    python: python(),
    py: python(),
    java: java(),
    cpp: cpp(),
    c: cpp(),
    rust: rust(),
    rs: rust(),
    php: php(),
    html: html(),
    htm: html(),
    css: css(),
    scss: css(),
    json: json(),
    markdown: markdown(),
    md: markdown(),
    xml: xml(),
    sql: sql(),
  };

  return langMap[lang] || [];
}

function initEditor() {
  if (!editorContainer.value) return;

  // Determine theme based on system preference
  const isDark =
    document.documentElement.classList.contains("dark") ||
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  const extensions = [
    basicSetup,
    keymap.of([
      ...defaultKeymap,
      indentWithTab,
      {
        key: "Mod-s",
        run: () => {
          if (modified.value && !props.readOnly) {
            saveFile();
          }
          return true;
        },
      },
    ]),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        const value = update.state.doc.toString();
        currentContent.value = value;
        emit("update:modelValue", value);
        emit("change", value);
      }
    }),
    EditorView.editable.of(!props.readOnly),
    getLanguageExtension(props.language),
  ];

  if (isDark) {
    extensions.push(oneDark);
  }

  const state = EditorState.create({
    doc: props.modelValue,
    extensions,
  });

  editor.value = new EditorView({
    state,
    parent: editorContainer.value,
  });
}

function saveFile() {
  if (!modified.value || saving.value) return;

  saving.value = true;
  emit(
    "save",
    currentContent.value,
    () => {
      // Callback after save
      originalContent.value = currentContent.value;
      saving.value = false;
      ElMessage.success("File saved successfully");
    },
    (error) => {
      // Error callback
      saving.value = false;
      ElMessage.error(error.message || "Failed to save file");
    },
  );
}

function resetContent() {
  if (editor.value) {
    editor.value.dispatch({
      changes: {
        from: 0,
        to: editor.value.state.doc.length,
        insert: originalContent.value,
      },
    });
    currentContent.value = originalContent.value;
  }
}

function updateTheme() {
  if (!editor.value) return;

  const isDark =
    document.documentElement.classList.contains("dark") ||
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  // Recreate editor with new theme
  const currentValue = editor.value.state.doc.toString();
  editor.value.destroy();
  initEditor();

  // Restore content
  if (currentValue !== props.modelValue) {
    editor.value.dispatch({
      changes: {
        from: 0,
        to: editor.value.state.doc.length,
        insert: currentValue,
      },
    });
  }
}

// Watch for theme changes
const observer = new MutationObserver(updateTheme);

watch(
  () => props.modelValue,
  (newValue) => {
    if (editor.value && newValue !== currentContent.value) {
      editor.value.dispatch({
        changes: {
          from: 0,
          to: editor.value.state.doc.length,
          insert: newValue,
        },
      });
      originalContent.value = newValue;
      currentContent.value = newValue;
    }
  },
);

onMounted(() => {
  initEditor();

  // Observe theme changes on document element
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
});

onUnmounted(() => {
  observer.disconnect();
  if (editor.value) {
    editor.value.destroy();
  }
});

// Expose methods for parent component
defineExpose({
  saveFile,
  resetContent,
  getValue: () => currentContent.value,
  setValue: (value) => {
    if (editor.value) {
      editor.value.dispatch({
        changes: {
          from: 0,
          to: editor.value.state.doc.length,
          insert: value,
        },
      });
    }
  },
});
</script>

<style scoped>
.code-editor-wrapper {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.dark .code-editor-wrapper {
  border-color: #374151;
  background: #1e1e1e;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.dark .editor-toolbar {
  border-bottom-color: #374151;
  background: #252526;
}

.editor-container {
  height: v-bind(height);
  width: 100%;
  overflow: auto;
}

.editor-container :deep(.cm-editor) {
  height: 100%;
  font-size: 14px;
  background: white;
}

.dark .editor-container :deep(.cm-editor) {
  background: #1e1e1e;
}

.editor-container :deep(.cm-scroller) {
  font-family:
    ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono",
    monospace;
}

.editor-container :deep(.cm-gutters) {
  background-color: #f6f8fa;
  border-right: 1px solid #e5e7eb;
}

.dark .editor-container :deep(.cm-gutters) {
  background-color: #0d1117;
  border-right: 1px solid #374151;
}
</style>
