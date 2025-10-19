<script setup>
import { computed } from "vue";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const baseModelList = computed(() => {
  if (!props.metadata.base_model) return [];
  return Array.isArray(props.metadata.base_model)
    ? props.metadata.base_model
    : [props.metadata.base_model];
});

const datasetList = computed(() => {
  if (!props.metadata.datasets) return [];
  return Array.isArray(props.metadata.datasets)
    ? props.metadata.datasets
    : [props.metadata.datasets];
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
      Relationships
    </h3>
    <div class="space-y-3">
      <!-- Base Models -->
      <div v-if="baseModelList.length > 0">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
          Based on:
        </div>
        <div class="space-y-1">
          <RouterLink
            v-for="model in baseModelList"
            :key="model"
            :to="`/models/${model}`"
            class="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
          >
            <div
              class="i-carbon-model text-base text-blue-500 dark:text-blue-400 flex-shrink-0"
            />
            <span
              class="text-sm text-blue-600 dark:text-blue-400 group-hover:underline truncate"
            >
              {{ model }}
            </span>
          </RouterLink>
        </div>
      </div>

      <!-- Training Datasets -->
      <div v-if="datasetList.length > 0">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-2">
          Trained on:
        </div>
        <div class="space-y-1">
          <RouterLink
            v-for="dataset in datasetList"
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
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
