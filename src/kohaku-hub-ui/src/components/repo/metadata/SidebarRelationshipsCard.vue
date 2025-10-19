<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  namespace: {
    type: String,
    required: true,
  },
  metadata: {
    type: Object,
    default: () => ({}),
  },
  repoType: {
    type: String,
    required: true,
  },
});

const INITIAL_SHOW = 2;
const baseModelsExpanded = ref(false);
const datasetsExpanded = ref(false);

const allBaseModels = computed(() => {
  if (!props.metadata.base_model) return [];
  return Array.isArray(props.metadata.base_model)
    ? props.metadata.base_model
    : [props.metadata.base_model];
});

const visibleBaseModels = computed(() => {
  if (baseModelsExpanded.value || allBaseModels.value.length <= INITIAL_SHOW) {
    return allBaseModels.value;
  }
  return allBaseModels.value.slice(0, INITIAL_SHOW);
});

const hasMoreBaseModels = computed(() => {
  return allBaseModels.value.length > INITIAL_SHOW;
});

const remainingBaseModels = computed(() => {
  return allBaseModels.value.length - INITIAL_SHOW;
});

const allDatasets = computed(() => {
  if (!props.metadata.datasets) return [];
  return Array.isArray(props.metadata.datasets)
    ? props.metadata.datasets
    : [props.metadata.datasets];
});

const visibleDatasets = computed(() => {
  if (datasetsExpanded.value || allDatasets.value.length <= INITIAL_SHOW) {
    return allDatasets.value;
  }
  return allDatasets.value.slice(0, INITIAL_SHOW);
});

const hasMoreDatasets = computed(() => {
  return allDatasets.value.length > INITIAL_SHOW;
});

const remainingDatasets = computed(() => {
  return allDatasets.value.length - INITIAL_SHOW;
});

const hasContent = computed(() => {
  return allBaseModels.value.length > 0 || allDatasets.value.length > 0;
});
</script>

<template>
  <div v-if="hasContent" class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
      Relationships
    </h3>
    <div class="space-y-3 text-sm">
      <!-- Author -->
      <div>
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Author:</div>
        <RouterLink
          :to="`/${namespace}`"
          class="flex items-center gap-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          <div
            class="i-carbon-user-avatar text-base text-gray-400 dark:text-gray-500 flex-shrink-0"
          />
          <span
            class="text-blue-600 dark:text-blue-400 hover:underline truncate"
            >{{ namespace }}</span
          >
        </RouterLink>
      </div>

      <!-- Base Models -->
      <div v-if="allBaseModels.length > 0">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
          Base Model:
        </div>
        <div class="space-y-1">
          <RouterLink
            v-for="model in visibleBaseModels"
            :key="model"
            :to="`/models/${model}`"
            class="flex items-center gap-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
          >
            <div
              class="i-carbon-model text-base text-blue-500 dark:text-blue-400 flex-shrink-0"
            />
            <span
              class="text-xs text-blue-600 dark:text-blue-400 group-hover:underline truncate"
            >
              {{ model }}
            </span>
          </RouterLink>
          <button
            v-if="hasMoreBaseModels"
            @click="baseModelsExpanded = !baseModelsExpanded"
            class="w-full py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors flex items-center justify-center gap-1"
          >
            <span v-if="!baseModelsExpanded"
              >Show {{ remainingBaseModels }} more</span
            >
            <span v-else>Show less</span>
            <div
              :class="
                baseModelsExpanded
                  ? 'i-carbon-chevron-up'
                  : 'i-carbon-chevron-down'
              "
              class="text-xs"
            />
          </button>
        </div>
      </div>

      <!-- Datasets -->
      <div v-if="allDatasets.length > 0">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
          Datasets:
        </div>
        <div class="space-y-1">
          <RouterLink
            v-for="dataset in visibleDatasets"
            :key="dataset"
            :to="`/datasets/${dataset}`"
            class="flex items-center gap-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors group"
          >
            <div
              class="i-carbon-data-set text-base text-green-500 dark:text-green-400 flex-shrink-0"
            />
            <span
              class="text-xs text-blue-600 dark:text-blue-400 group-hover:underline truncate"
            >
              {{ dataset }}
            </span>
          </RouterLink>
          <button
            v-if="hasMoreDatasets"
            @click="datasetsExpanded = !datasetsExpanded"
            class="w-full py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors flex items-center justify-center gap-1"
          >
            <span v-if="!datasetsExpanded"
              >Show {{ remainingDatasets }} more</span
            >
            <span v-else>Show less</span>
            <div
              :class="
                datasetsExpanded
                  ? 'i-carbon-chevron-up'
                  : 'i-carbon-chevron-down'
              "
              class="text-xs"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
