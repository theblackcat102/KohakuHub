<script setup>
import { ref, computed } from "vue";
import { formatBytes, detectFormat } from "./api";

const props = defineProps({
  files: {
    type: Array,
    required: true,
  },
});

const emit = defineEmits(["select"]);

const filter = ref("");

// Filter files
const filteredFiles = computed(() => {
  if (!filter.value) return props.files;

  const query = filter.value.toLowerCase();
  return props.files.filter((f) => f.name.toLowerCase().includes(query));
});

// Group files by directory
const groupedFiles = computed(() => {
  const groups = {};

  for (const file of filteredFiles.value) {
    const parts = file.name.split("/");
    const dir = parts.length > 1 ? parts.slice(0, -1).join("/") : "/";

    if (!groups[dir]) {
      groups[dir] = [];
    }

    groups[dir].push({
      ...file,
      basename: parts[parts.length - 1],
    });
  }

  return groups;
});

// Check if file is previewable
function isPreviewable(fileName) {
  const format = detectFormat(fileName);
  return format && format !== "tar";
}

// Handle file selection
function selectFile(file) {
  if (!isPreviewable(file.name)) {
    return;
  }
  emit("select", file);
}
</script>

<template>
  <div class="tar-file-list">
    <!-- Header -->
    <div class="header p-4 border-b border-gray-200 dark:border-gray-700">
      <h4 class="text-lg font-semibold mb-2">Archive Contents</h4>
      <input
        v-model="filter"
        type="text"
        placeholder="Filter files..."
        class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-black dark:text-white"
      />
    </div>

    <!-- File list -->
    <div class="file-list overflow-auto" style="max-height: 500px">
      <div
        v-for="(files, dir) in groupedFiles"
        :key="dir"
        class="directory-group"
      >
        <!-- Directory header -->
        <div
          class="directory-header px-4 py-2 bg-gray-100 dark:bg-gray-800 text-sm font-semibold sticky top-0"
        >
          📁 {{ dir }}
        </div>

        <!-- Files in directory -->
        <div
          v-for="file in files"
          :key="file.name"
          class="file-item px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800"
          :class="{
            'cursor-pointer': isPreviewable(file.name),
            'opacity-50 cursor-not-allowed': !isPreviewable(file.name),
          }"
          @click="selectFile(file)"
        >
          <div class="file-info flex-1">
            <div class="file-name font-medium">
              {{ file.basename }}
            </div>
            <div class="file-size text-sm text-gray-600 dark:text-gray-400">
              {{ formatBytes(file.size) }}
            </div>
          </div>

          <div
            v-if="isPreviewable(file.name)"
            class="preview-badge px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs"
          >
            Preview →
          </div>
          <div
            v-else
            class="not-previewable text-xs text-gray-500 dark:text-gray-500"
          >
            Not previewable
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="filteredFiles.length === 0"
      class="empty-state p-8 text-center text-gray-600 dark:text-gray-400"
    >
      No files found
    </div>
  </div>
</template>

<style scoped>
.file-item {
  transition: background-color 0.15s;
}
</style>
