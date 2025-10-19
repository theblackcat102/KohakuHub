<script setup>
import { computed } from "vue";
import LicenseCard from "./LicenseCard.vue";
import LanguageCard from "./LanguageCard.vue";
import FrameworkCard from "./FrameworkCard.vue";
import MetricsCard from "./MetricsCard.vue";
import { formatMetadataKey } from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
  repoType: {
    type: String,
    required: true,
  },
});

const hasAnyContent = computed(() => {
  return Object.keys(props.metadata).length > 0;
});

// All metadata fields except the specialized ones we show as dedicated cards
const specializedFields = new Set([
  "license",
  "license_name",
  "license_link",
  "language",
  "library_name",
  "pipeline_tag",
  "base_model",
  "datasets",
  "task_categories",
  "size_categories",
  "multilinguality",
  "annotations_creators",
  "source_datasets",
  "eval_results",
]);

const otherFields = computed(() => {
  const others = [];
  for (const [key, value] of Object.entries(props.metadata)) {
    if (!specializedFields.has(key)) {
      others.push({ key, value });
    }
  }
  return others.sort((a, b) => a.key.localeCompare(b.key));
});

function formatValue(value) {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  if (Array.isArray(value)) return value;
  if (typeof value === "object" && value !== null) return value;
  return String(value);
}
</script>

<template>
  <div
    v-if="hasAnyContent"
    class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
  >
    <!-- License -->
    <LicenseCard v-if="metadata.license" :metadata="metadata" />

    <!-- Languages -->
    <LanguageCard v-if="metadata.language" :languages="metadata.language" />

    <!-- Framework (Models) -->
    <FrameworkCard
      v-if="
        repoType === 'model' && (metadata.library_name || metadata.pipeline_tag)
      "
      :metadata="metadata"
    />

    <!-- Base Models (Models) -->
    <div v-if="repoType === 'model' && metadata.base_model" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        Base Model
      </h3>
      <div class="space-y-1">
        <RouterLink
          v-for="model in Array.isArray(metadata.base_model)
            ? metadata.base_model
            : [metadata.base_model]"
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

    <!-- Training Datasets (Models) -->
    <div v-if="repoType === 'model' && metadata.datasets" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        Training Datasets
      </h3>
      <div class="space-y-1">
        <RouterLink
          v-for="dataset in Array.isArray(metadata.datasets)
            ? metadata.datasets
            : [metadata.datasets]"
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

    <!-- Task Categories (Datasets) -->
    <div v-if="repoType === 'dataset' && metadata.task_categories" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        Task Categories
      </h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="task in Array.isArray(metadata.task_categories)
            ? metadata.task_categories
            : [metadata.task_categories]"
          :key="task"
          size="small"
          type="success"
        >
          {{ task }}
        </el-tag>
      </div>
    </div>

    <!-- Size Category (Datasets) -->
    <div v-if="repoType === 'dataset' && metadata.size_categories" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">Size</h3>
      <el-tag size="large" type="info">
        {{
          Array.isArray(metadata.size_categories)
            ? metadata.size_categories[0]
            : metadata.size_categories
        }}
      </el-tag>
    </div>

    <!-- Multilinguality (Datasets) -->
    <div v-if="repoType === 'dataset' && metadata.multilinguality" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        Multilinguality
      </h3>
      <div class="text-sm text-gray-900 dark:text-white">
        {{ metadata.multilinguality }}
      </div>
    </div>

    <!-- Annotations Creators (Datasets) -->
    <div
      v-if="repoType === 'dataset' && metadata.annotations_creators"
      class="card"
    >
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        Annotations
      </h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="creator in Array.isArray(metadata.annotations_creators)
            ? metadata.annotations_creators
            : [metadata.annotations_creators]"
          :key="creator"
          size="small"
        >
          {{ creator }}
        </el-tag>
      </div>
    </div>

    <!-- Source Datasets (Datasets) -->
    <div v-if="repoType === 'dataset' && metadata.source_datasets" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">Source</h3>
      <div class="flex flex-wrap gap-2">
        <el-tag
          v-for="source in Array.isArray(metadata.source_datasets)
            ? metadata.source_datasets
            : [metadata.source_datasets]"
          :key="source"
          size="small"
          type="warning"
        >
          {{ source }}
        </el-tag>
      </div>
    </div>

    <!-- Metrics (Models) -->
    <MetricsCard
      v-if="repoType === 'model' && metadata.eval_results"
      :results="metadata.eval_results"
    />

    <!-- All Other Fields (Each as individual card) -->
    <div v-for="field in otherFields" :key="field.key" class="card">
      <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
        {{ formatMetadataKey(field.key) }}
      </h3>
      <div class="text-sm">
        <!-- String value -->
        <div
          v-if="typeof field.value === 'string'"
          class="text-gray-900 dark:text-white"
        >
          {{ field.value }}
        </div>
        <!-- Number or boolean -->
        <div
          v-else-if="
            typeof field.value === 'number' || typeof field.value === 'boolean'
          "
          class="text-gray-900 dark:text-white"
        >
          {{ field.value }}
        </div>
        <!-- Array -->
        <div
          v-else-if="Array.isArray(field.value)"
          class="flex flex-wrap gap-2"
        >
          <el-tag v-for="(item, idx) in field.value" :key="idx" size="small">
            {{ item }}
          </el-tag>
        </div>
        <!-- Object -->
        <pre
          v-else
          class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto"
        ><code class="text-gray-900 dark:text-gray-100">{{ JSON.stringify(field.value, null, 2) }}</code></pre>
      </div>
    </div>
  </div>
</template>
