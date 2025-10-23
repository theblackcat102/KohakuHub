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
</script>

<template>
  <div class="data-grid-container">
    <!-- Truncation warning -->
    <div
      v-if="truncated"
      class="warning p-3 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-700"
    >
      <span class="text-yellow-800 dark:text-yellow-200">
        ⚠️ Showing first {{ rows.length }} rows. File contains more data.
      </span>
    </div>

    <!-- Data table -->
    <div class="table-wrapper overflow-auto">
      <table class="data-table w-full border-collapse">
        <thead class="sticky top-0 bg-gray-50 dark:bg-gray-800">
          <tr>
            <th
              v-for="column in columns"
              :key="column"
              class="column-header px-4 py-3 text-left text-sm font-semibold border-b-2 border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="toggleSort(column)"
            >
              <div class="flex items-center gap-2">
                <span>{{ column }}</span>
                <span v-if="sortColumn === column" class="sort-indicator">
                  {{ sortDirection === "asc" ? "↑" : "↓" }}
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rowIndex) in sortedRows"
            :key="rowIndex"
            class="hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <td
              v-for="(value, colIndex) in row"
              :key="colIndex"
              class="cell px-4 py-2 text-sm border-b border-gray-200 dark:border-gray-700"
            >
              {{ formatValue(value) }}
            </td>
          </tr>
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
  color: #3b82f6;
  font-weight: bold;
}
</style>
