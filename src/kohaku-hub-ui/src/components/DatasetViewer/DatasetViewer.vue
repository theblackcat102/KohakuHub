<script setup>
import { ref, computed, watch } from "vue";
import {
  previewFile,
  executeSQLQuery,
  listTARFiles,
  extractTARFile,
  detectFormat,
  formatBytes,
} from "./api";
import DataGridEnhanced from "./DataGridEnhanced.vue";
import TARFileList from "./TARFileList.vue";

const props = defineProps({
  fileUrl: {
    type: String,
    required: true,
  },
  fileName: {
    type: String,
    required: true,
  },
  maxRows: {
    type: Number,
    default: 100,
  },
  sqlQuery: {
    type: String,
    default: "",
  },
  useSQL: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["error", "warning", "row-selected", "data-loaded"]);

const loading = ref(false);
const error = ref(null);
const previewData = ref(null);
const fileFormat = ref(null);
const actualMaxRows = ref(null); // Track actual limit used (for SQL vs regular preview)

// TAR-specific state
const isTAR = ref(false);
const tarFiles = ref([]);
const selectedTARFile = ref(null);

// Handle row selection from DataGrid - emit to parent
function handleRowSelected(index) {
  emit("row-selected", index);
}

// Load preview
async function loadPreview() {
  loading.value = true;
  error.value = null;
  previewData.value = null;

  try {
    // Detect format
    fileFormat.value = detectFormat(props.fileName);

    if (!fileFormat.value) {
      throw new Error("Unsupported file format");
    }

    // Handle TAR archives differently
    if (fileFormat.value === "tar") {
      isTAR.value = true;
      await loadTARFiles();
    } else {
      isTAR.value = false;
      await loadFilePreview(props.fileUrl, fileFormat.value);
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message;
    emit("error", error.value);
  } finally {
    loading.value = false;
  }
}

// Load TAR file listing
async function loadTARFiles() {
  const result = await listTARFiles(props.fileUrl);
  tarFiles.value = result.files;
}

// Handle TAR file selection
async function selectTARFile(file) {
  selectedTARFile.value = file;
  loading.value = true;
  error.value = null;

  try {
    // Extract file from TAR
    const blob = await extractTARFile(props.fileUrl, file.name);

    // Create temporary URL for extracted file
    const tempUrl = URL.createObjectURL(blob);

    // Detect format from file name
    const extractedFormat = detectFormat(file.name);

    if (!extractedFormat || extractedFormat === "tar") {
      throw new Error("Cannot preview this file type");
    }

    // Preview extracted file
    await loadFilePreview(tempUrl, extractedFormat);

    // Cleanup temp URL
    URL.revokeObjectURL(tempUrl);
  } catch (err) {
    error.value = err.response?.data?.detail || err.message;
    selectedTARFile.value = null;
  } finally {
    loading.value = false;
  }
}

// Load file preview (non-TAR)
async function loadFilePreview(url, format) {
  // Use SQL query if enabled
  if (props.useSQL && props.sqlQuery.trim()) {
    // Check for LIMIT clause
    const queryUpper = props.sqlQuery.toUpperCase();
    if (!queryUpper.includes("LIMIT")) {
      emit("warning", "No LIMIT clause found - adding LIMIT 10 automatically");
    }

    const sqlMaxRows = 10; // Default LIMIT 10 for wide tables
    actualMaxRows.value = sqlMaxRows;

    const result = await executeSQLQuery(url, props.sqlQuery, {
      format,
      maxRows: sqlMaxRows,
    });
    previewData.value = result;
  } else {
    // Regular preview
    actualMaxRows.value = props.maxRows;

    const result = await previewFile(url, {
      format,
      maxRows: props.maxRows,
    });
    previewData.value = result;
  }

  // Emit data loaded event to parent
  if (previewData.value) {
    emit("data-loaded", previewData.value);
  }
}

// Watch for URL changes
watch(() => props.fileUrl, loadPreview, { immediate: true });

// Stats
const stats = computed(() => {
  if (!previewData.value) return null;

  return {
    columns: previewData.value.columns.length,
    rows: previewData.value.total_rows,
    truncated: previewData.value.truncated,
    maxRows: actualMaxRows.value || props.maxRows, // Use actual limit
    fileSize: formatBytes(previewData.value.file_size),
  };
});
</script>

<template>
  <div
    class="dataset-viewer bg-white dark:bg-gray-900 text-black dark:text-white"
  >
    <!-- Header -->
    <div class="header p-4 border-b border-gray-200 dark:border-gray-700">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold">{{ fileName }}</h3>
          <div
            v-if="stats"
            class="text-sm text-gray-600 dark:text-gray-400 mt-1"
          >
            {{ stats.columns }} columns × {{ stats.rows }} rows
            <span
              v-if="stats.truncated"
              class="text-yellow-600 dark:text-yellow-400"
            >
              (truncated to {{ stats.maxRows }} rows)
            </span>
            <span v-if="stats.fileSize !== 'Unknown'" class="ml-2">
              · {{ stats.fileSize }}
            </span>
          </div>
        </div>

        <div
          v-if="fileFormat"
          class="badge px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm"
        >
          {{ fileFormat.toUpperCase() }}
        </div>
      </div>

      <!-- TAR file indicator -->
      <div
        v-if="selectedTARFile"
        class="mt-2 text-sm text-gray-600 dark:text-gray-400"
      >
        Viewing: {{ selectedTARFile.name }} ({{
          formatBytes(selectedTARFile.size)
        }})
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading p-8 text-center">
      <div
        class="spinner inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"
      ></div>
      <div class="mt-2 text-gray-600 dark:text-gray-400">
        Loading preview...
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error p-8 text-center">
      <div class="text-red-600 dark:text-red-400 text-lg">⚠️ Error</div>
      <div class="mt-2 text-gray-700 dark:text-gray-300">{{ error }}</div>
    </div>

    <!-- TAR file listing -->
    <div v-else-if="isTAR && !selectedTARFile" class="tar-listing">
      <TARFileList :files="tarFiles" @select="selectTARFile" />
    </div>

    <!-- Data grid -->
    <div v-else-if="previewData" class="data-grid">
      <DataGridEnhanced
        :columns="previewData.columns"
        :rows="previewData.rows"
        :truncated="previewData.truncated"
        @row-selected="handleRowSelected"
      />
    </div>

    <!-- No data -->
    <div
      v-else
      class="no-data p-8 text-center text-gray-600 dark:text-gray-400"
    >
      No data to display
    </div>
  </div>
</template>

<style scoped>
.dataset-viewer {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.dark .dataset-viewer {
  border-color: #374151;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
