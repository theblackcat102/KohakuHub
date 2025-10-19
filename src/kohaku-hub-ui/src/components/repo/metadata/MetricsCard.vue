<script setup>
import { computed } from "vue";

const props = defineProps({
  results: {
    type: Array,
    required: true,
  },
});

const formattedResults = computed(() => {
  if (!props.results || !Array.isArray(props.results)) return [];

  return props.results.map((result) => ({
    task: result.task || result.task_type || "Unknown Task",
    dataset: result.dataset || "Unknown Dataset",
    metrics: result.metrics || {},
  }));
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">Evaluation</h3>
    <div class="space-y-4">
      <div
        v-for="(result, idx) in formattedResults"
        :key="idx"
        class="border-b border-gray-200 dark:border-gray-700 last:border-0 pb-3 last:pb-0"
      >
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
          {{ result.task }}
          <span v-if="result.dataset !== 'Unknown Dataset'">
            on {{ result.dataset }}</span
          >
        </div>
        <div class="space-y-1">
          <div
            v-for="(value, metric) in result.metrics"
            :key="metric"
            class="flex justify-between items-center text-sm"
          >
            <span class="text-gray-700 dark:text-gray-300">{{ metric }}:</span>
            <span class="font-semibold text-gray-900 dark:text-white">
              {{ typeof value === "number" ? value.toFixed(4) : value }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
