<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  datasets: {
    type: Array,
    required: true,
  },
});

const expanded = ref(false);
const INITIAL_SHOW = 3;

const datasetList = computed(() => {
  return props.datasets || [];
});

const visibleDatasets = computed(() => {
  if (expanded.value || datasetList.value.length <= INITIAL_SHOW) {
    return datasetList.value;
  }
  return datasetList.value.slice(0, INITIAL_SHOW);
});

const hasMore = computed(() => {
  return datasetList.value.length > INITIAL_SHOW;
});

const remainingCount = computed(() => {
  return datasetList.value.length - INITIAL_SHOW;
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
      Referenced Datasets
    </h3>
    <div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
      Datasets used or referenced:
    </div>
    <div class="space-y-1">
      <RouterLink
        v-for="dataset in visibleDatasets"
        :key="dataset"
        :to="`/datasets/${dataset}`"
        class="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
      >
        <div
          class="i-carbon-data-set text-base text-green-500 dark:text-green-400 flex-shrink-0"
        />
        <span
          class="text-sm text-blue-600 dark:text-blue-400 group-hover:underline truncate"
        >
          {{ dataset }}
        </span>
        <div
          class="i-carbon-arrow-right text-xs opacity-0 group-hover:opacity-100 transition-opacity ml-auto flex-shrink-0"
        />
      </RouterLink>
    </div>

    <!-- Show More/Less Button -->
    <button
      v-if="hasMore"
      @click="expanded = !expanded"
      class="w-full mt-2 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors flex items-center justify-center gap-1"
    >
      <span v-if="!expanded">Show {{ remainingCount }} more</span>
      <span v-else>Show less</span>
      <div
        :class="expanded ? 'i-carbon-chevron-up' : 'i-carbon-chevron-down'"
        class="text-xs"
      />
    </button>
  </div>
</template>
