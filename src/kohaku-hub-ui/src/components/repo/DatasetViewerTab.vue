<script setup>
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import DatasetViewer from "@/components/DatasetViewer/DatasetViewer.vue";
import { detectFormat } from "@/components/DatasetViewer/api";

const props = defineProps({
  repoType: {
    type: String,
    required: true,
  },
  namespace: {
    type: String,
    required: true,
  },
  name: {
    type: String,
    required: true,
  },
  branch: {
    type: String,
    default: "main",
  },
  files: {
    type: Array,
    default: () => [],
  },
});

const selectedFile = ref(null);
const fileUrl = ref(null);
const loadingUrl = ref(false);

// Query parameters
const maxRows = ref(100);
const sqlQuery = ref("SELECT * FROM dataset LIMIT 100");
const useSQL = ref(false);
const sqlWarning = ref("");

// Trigger key to force reload
const reloadKey = ref(0);

// Check if SQL is supported for current file
const sqlSupported = computed(() => {
  if (!selectedFile.value) return false;
  const format = detectFormat(selectedFile.value.path);
  return format === "csv" || format === "parquet";
});

// Validate and apply query
function applyQuery() {
  sqlWarning.value = "";

  // If using SQL, check for LIMIT clause
  if (useSQL.value && sqlQuery.value.trim()) {
    const queryUpper = sqlQuery.value.toUpperCase();
    if (!queryUpper.includes("LIMIT")) {
      sqlWarning.value =
        "No LIMIT found - automatically adding LIMIT 10000 for safety";
      // Backend will add LIMIT automatically
    }
  }

  reloadKey.value++;
}

// Filter previewable files
const previewableFiles = computed(() => {
  return props.files
    .filter((file) => file.type !== "directory")
    .filter((file) => {
      const format = detectFormat(file.path);
      return format && format !== "tar"; // Exclude TAR for now
    })
    .sort((a, b) => a.path.localeCompare(b.path));
});

// Group files by directory
const groupedFiles = computed(() => {
  const groups = {};

  for (const file of previewableFiles.value) {
    const parts = file.path.split("/");
    const dir = parts.length > 1 ? parts.slice(0, -1).join("/") : "/";

    if (!groups[dir]) {
      groups[dir] = [];
    }

    groups[dir].push({
      ...file,
      basename: parts[parts.length - 1],
      format: detectFormat(file.path),
    });
  }

  return groups;
});

// Select a file and get presigned URL
async function selectFile(file) {
  selectedFile.value = file;
  loadingUrl.value = true;
  fileUrl.value = null;

  try {
    // Get presigned URL by making HEAD request (follows redirect)
    const url = `/${props.repoType}s/${props.namespace}/${props.name}/resolve/${props.branch}/${file.path}`;

    const response = await fetch(url, { method: "HEAD" });

    if (!response.ok) {
      throw new Error(`Failed to get file URL: ${response.statusText}`);
    }

    // Get the final URL after redirect
    fileUrl.value = response.url;
  } catch (err) {
    ElMessage.error({
      message: `Failed to load file: ${err.message}`,
      duration: 5000,
    });
    selectedFile.value = null;
  } finally {
    loadingUrl.value = false;
  }
}

// Handle error from DatasetViewer
function handleViewerError(error) {
  ElMessage.error({
    message: `Preview error: ${error}`,
    duration: 5000,
  });
}

// Format file size
function formatSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

// Auto-select first file if available
watch(
  () => previewableFiles.value,
  (files) => {
    if (files.length > 0 && !selectedFile.value) {
      selectFile(files[0]);
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="dataset-viewer-tab">
    <!-- Full width layout: File list on left, Viewer on right -->
    <div class="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
      <!-- File List Sidebar -->
      <div class="file-sidebar">
        <div class="card p-0 h-fit">
          <!-- Header -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-base font-semibold">Previewable Files</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {{ previewableFiles.length }} file{{
                previewableFiles.length !== 1 ? "s" : ""
              }}
            </p>
          </div>

          <!-- File List (Scrollable) -->
          <div
            class="file-list-scroll overflow-y-auto"
            style="max-height: 300px"
          >
            <!-- No files -->
            <div
              v-if="previewableFiles.length === 0"
              class="text-center py-8 px-4 text-gray-600 dark:text-gray-400"
            >
              <div class="i-carbon-document-blank text-4xl mb-2 inline-block" />
              <p class="text-sm">No previewable files</p>
              <p class="text-xs mt-1">Supported: CSV, JSON, JSONL, Parquet</p>
            </div>

            <!-- File groups -->
            <div v-else class="py-2">
              <div
                v-for="(files, dir) in groupedFiles"
                :key="dir"
                class="file-group mb-2"
              >
                <!-- Directory header -->
                <div
                  v-if="dir !== '/'"
                  class="text-xs font-semibold text-gray-500 dark:text-gray-400 px-3 py-1"
                >
                  <div class="i-carbon-folder inline-block mr-1" />
                  {{ dir }}
                </div>

                <!-- Files in directory -->
                <div
                  v-for="file in files"
                  :key="file.path"
                  class="file-item px-3 py-2 cursor-pointer transition-all"
                  :class="[
                    selectedFile?.path === file.path
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-800',
                  ]"
                  @click="selectFile(file)"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <div class="text-sm font-medium truncate">
                        {{ file.basename }}
                      </div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">
                        {{ formatSize(file.size) }}
                      </div>
                    </div>
                    <div
                      class="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-mono flex-shrink-0"
                    >
                      {{ file.format.toUpperCase() }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Query Parameters -->
          <div
            class="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3"
          >
            <!-- SQL Mode Toggle (only for CSV/Parquet) -->
            <div v-if="sqlSupported">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="useSQL"
                  type="checkbox"
                  class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                />
                <span
                  class="text-xs font-semibold text-gray-700 dark:text-gray-300"
                >
                  Use SQL Query
                </span>
              </label>
            </div>

            <!-- SQL Query Input -->
            <div v-if="useSQL && sqlSupported">
              <label
                class="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1"
              >
                SQL Query
              </label>
              <textarea
                v-model="sqlQuery"
                placeholder="SELECT * FROM dataset LIMIT 100"
                rows="4"
                class="w-full px-2 py-1.5 text-xs font-mono border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-black dark:text-white resize-none"
              />
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Use 'dataset' as table name
              </div>

              <!-- SQL Warning -->
              <div
                v-if="sqlWarning"
                class="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded text-xs text-yellow-800 dark:text-yellow-200"
              >
                ⚠️ {{ sqlWarning }}
              </div>
            </div>

            <!-- Simple mode (no SQL) - Show max rows selector -->
            <div v-if="!useSQL || !sqlSupported">
              <label
                class="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-1"
              >
                Max Rows
              </label>
              <select
                v-model.number="maxRows"
                class="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-black dark:text-white"
              >
                <option :value="100">100 rows</option>
                <option :value="500">500 rows</option>
                <option :value="1000">1,000 rows</option>
                <option :value="5000">5,000 rows</option>
                <option :value="10000">10,000 rows</option>
              </select>
            </div>

            <!-- Apply Button -->
            <button
              @click="applyQuery"
              class="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-sm transition-colors"
              :disabled="useSQL && !sqlQuery.trim()"
            >
              {{ useSQL ? "Run Query" : "Reload (First 100 Rows)" }}
            </button>

            <!-- Quick query examples (SQL mode) -->
            <div v-if="useSQL && sqlSupported" class="text-xs space-y-1">
              <div class="font-semibold text-gray-600 dark:text-gray-400">
                Quick queries:
              </div>
              <button
                @click="sqlQuery = 'SELECT * FROM dataset LIMIT 100'"
                class="block w-full text-left px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              >
                First 100 rows
              </button>
              <button
                @click="
                  sqlQuery = 'SELECT * FROM dataset ORDER BY RANDOM() LIMIT 100'
                "
                class="block w-full text-left px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              >
                Random 100 rows
              </button>
              <button
                @click="sqlQuery = 'SELECT COUNT(*) as total FROM dataset'"
                class="block w-full text-left px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              >
                Count all rows
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Viewer Panel (Full Width) -->
      <div class="viewer-panel min-w-0">
        <!-- Loading state -->
        <div v-if="loadingUrl" class="card text-center py-20">
          <el-icon class="is-loading" :size="40">
            <div class="i-carbon-loading" />
          </el-icon>
          <p class="mt-4 text-gray-600 dark:text-gray-400">
            Loading file URL...
          </p>
        </div>

        <!-- No file selected -->
        <div
          v-else-if="!selectedFile"
          class="card text-center py-20 text-gray-600 dark:text-gray-400"
        >
          <div class="i-carbon-data-table text-6xl mb-4 inline-block" />
          <p>Select a file to preview</p>
        </div>

        <!-- Dataset Viewer -->
        <DatasetViewer
          v-else-if="fileUrl"
          :key="reloadKey"
          :file-url="fileUrl"
          :file-name="selectedFile.path"
          :max-rows="maxRows"
          :sql-query="sqlQuery"
          :use-s-q-l="useSQL"
          @error="handleViewerError"
          @warning="(msg) => (sqlWarning = msg)"
        />
      </div>
    </div>

    <!-- Attribution Notice (Kohaku License requirement) -->
    <div
      class="mt-6 p-3 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700"
    >
      <div class="text-xs text-gray-600 dark:text-gray-400">
        <div class="flex items-center gap-2 mb-1">
          <div class="i-carbon-information" />
          <span class="font-semibold">Dataset Viewer</span>
        </div>
        <p class="text-xs">
          Licensed under Kohaku Software License by KohakuBlueLeaf. Commercial
          usage exceeding trial limits ($25k/year OR 3 months) requires a
          commercial license.
          <a
            href="mailto:kohaku@kblueleaf.net"
            class="text-blue-600 dark:text-blue-400 hover:underline"
          >
            Contact for licensing
          </a>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-item {
  user-select: none;
}

.file-list-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgb(209 213 219) transparent;
}

.dark .file-list-scroll {
  scrollbar-color: rgb(75 85 99) transparent;
}

.file-list-scroll::-webkit-scrollbar {
  width: 6px;
}

.file-list-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.file-list-scroll::-webkit-scrollbar-thumb {
  background-color: rgb(209 213 219);
  border-radius: 3px;
}

.dark .file-list-scroll::-webkit-scrollbar-thumb {
  background-color: rgb(75 85 99);
}
</style>
