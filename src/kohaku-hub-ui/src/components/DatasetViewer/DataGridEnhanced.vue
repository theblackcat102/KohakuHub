<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  columns: {
    type: Array,
    required: true,
  },
  rows: {
    type: Array,
    required: true,
  },
  truncated: {
    type: Boolean,
    default: false,
  },
});

// Sorting
const sortColumn = ref(null);
const sortDirection = ref("asc");

// Row detail
const selectedRowIndex = ref(null);

// Max cell length before truncation
const MAX_CELL_LENGTH = 100;

// Sorting logic
const sortedRows = computed(() => {
  if (!sortColumn.value) return props.rows;

  const colIndex = props.columns.indexOf(sortColumn.value);
  if (colIndex === -1) return props.rows;

  const sorted = [...props.rows].sort((a, b) => {
    const aVal = a[colIndex];
    const bVal = b[colIndex];

    // Handle null/undefined
    if (aVal == null) return 1;
    if (bVal == null) return -1;

    // Numeric comparison
    if (typeof aVal === "number" && typeof bVal === "number") {
      return aVal - bVal;
    }

    // String comparison
    return String(aVal).localeCompare(String(bVal));
  });

  return sortDirection.value === "desc" ? sorted.reverse() : sorted;
});

// Toggle sort
function toggleSort(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
  } else {
    sortColumn.value = column;
    sortDirection.value = "asc";
  }
}

// Format cell value
function formatValue(value) {
  if (value == null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

// Check if cell is long
function isCellLong(value) {
  const formatted = formatValue(value);
  return formatted.length > MAX_CELL_LENGTH;
}

// Truncate cell value
function truncateValue(value) {
  const formatted = formatValue(value);
  if (formatted.length <= MAX_CELL_LENGTH) return formatted;
  return formatted.substring(0, MAX_CELL_LENGTH) + "...";
}

// Check if value is an image (base64 or binary indicator)
function isImage(value) {
  if (!value) return false;
  const str = String(value);
  // Check for base64 image data URL
  if (str.startsWith("data:image/")) return true;
  // Check for <binary> indicator from backend
  if (str.startsWith("<binary:") || str.startsWith("<large file:"))
    return false;
  // Check for very long strings that might be base64 (but not detect as image without data URL)
  return false;
}

// Get image data URL
function getImageDataUrl(value) {
  const str = String(value);
  if (str.startsWith("data:image/")) return str;
  // If it's base64 without prefix, add it
  if (str.length > 100 && !str.includes(" ")) {
    return `data:image/png;base64,${str}`;
  }
  return null;
}

// Toggle row detail
function toggleRowDetail(index) {
  if (selectedRowIndex.value === index) {
    selectedRowIndex.value = null;
  } else {
    selectedRowIndex.value = index;
  }
}
</script>

<template>
  <div class="data-grid-enhanced">
    <!-- Truncation warning -->
    <div
      v-if="truncated"
      class="warning p-3 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-700"
    >
      <span class="text-yellow-800 dark:text-yellow-200">
        Showing first {{ rows.length }} rows. File contains more data.
      </span>
    </div>

    <!-- Data table -->
    <div class="table-wrapper overflow-auto">
      <table class="data-table w-full border-collapse">
        <thead class="sticky top-0 bg-gray-50 dark:bg-gray-800">
          <tr>
            <th
              class="column-header px-2 py-3 text-left text-sm font-semibold border-b-2 border-gray-200 dark:border-gray-700"
              style="width: 40px"
            >
              #
            </th>
            <th
              v-for="column in columns"
              :key="column"
              class="column-header px-4 py-3 text-left text-sm font-semibold border-b-2 border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="toggleSort(column)"
            >
              <div class="flex items-center gap-2">
                <span>{{ column }}</span>
                <span
                  v-if="sortColumn === column"
                  class="sort-indicator text-blue-500"
                >
                  {{ sortDirection === "asc" ? "↑" : "↓" }}
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(row, rowIndex) in sortedRows" :key="rowIndex">
            <!-- Main row -->
            <tr
              class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
              @click="toggleRowDetail(rowIndex)"
              :class="{
                'bg-blue-50 dark:bg-blue-900/20': selectedRowIndex === rowIndex,
              }"
            >
              <td
                class="cell px-2 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700"
              >
                {{ rowIndex + 1 }}
              </td>
              <td
                v-for="(value, colIndex) in row"
                :key="colIndex"
                class="cell px-4 py-2 text-sm border-b border-gray-200 dark:border-gray-700"
                :class="{
                  'text-blue-600 dark:text-blue-400': isCellLong(value),
                }"
              >
                {{ truncateValue(value) }}
              </td>
            </tr>

            <!-- Detail row (expanded) -->
            <tr
              v-if="selectedRowIndex === rowIndex"
              class="detail-row bg-gray-100 dark:bg-gray-800"
            >
              <td
                :colspan="columns.length + 1"
                class="p-4 border-b border-gray-300 dark:border-gray-600"
              >
                <div class="detail-content">
                  <div
                    class="text-sm font-semibold mb-3 text-gray-700 dark:text-gray-300"
                  >
                    Row {{ rowIndex + 1 }} Details
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                      v-for="(value, colIndex) in row"
                      :key="colIndex"
                      class="detail-field p-3 bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700"
                    >
                      <div
                        class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1"
                      >
                        {{ columns[colIndex] }}
                      </div>

                      <!-- Image value -->
                      <div v-if="isImage(value)" class="image-preview">
                        <img
                          :src="getImageDataUrl(value)"
                          alt="Preview"
                          class="max-w-full max-h-48 border border-gray-300 dark:border-gray-600 rounded"
                        />
                      </div>

                      <!-- Text value -->
                      <div
                        v-else
                        class="text-sm text-gray-900 dark:text-gray-100 break-words font-mono whitespace-pre-wrap"
                      >
                        {{ formatValue(value) }}
                      </div>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div
      v-if="rows.length === 0"
      class="empty-state p-8 text-center text-gray-600 dark:text-gray-400"
    >
      No rows to display
    </div>
  </div>
</template>

<style scoped>
.table-wrapper {
  max-height: 600px;
}

.data-table {
  font-variant-numeric: tabular-nums;
}

.cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-header {
  user-select: none;
}

.sort-indicator {
  font-weight: bold;
}

.detail-row {
  border-left: 4px solid #3b82f6;
}

.detail-content {
  max-height: 600px;
  overflow-y: auto;
}

.detail-field {
  transition: all 0.15s;
}

.detail-field:hover {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
