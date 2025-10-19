<script setup>
import { computed } from "vue";
import {
  getTaskCategoryName,
  formatSizeCategory,
  formatMetadataKey,
} from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const taskCategories = computed(() => {
  if (!props.metadata.task_categories) return [];
  return Array.isArray(props.metadata.task_categories)
    ? props.metadata.task_categories
    : [props.metadata.task_categories];
});

const sizeCategory = computed(() => {
  const size = props.metadata.size_categories;
  if (!size) return null;
  const sizeStr = Array.isArray(size) ? size[0] : size;
  return formatSizeCategory(sizeStr);
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
      Dataset Info
    </h3>
    <div class="space-y-3 text-sm">
      <!-- Task Categories -->
      <div v-if="taskCategories.length > 0">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Tasks:</div>
        <div class="flex flex-wrap gap-1">
          <el-tag
            v-for="task in taskCategories"
            :key="task"
            size="small"
            type="success"
          >
            {{ getTaskCategoryName(task) }}
          </el-tag>
        </div>
      </div>

      <!-- Size Category -->
      <div v-if="sizeCategory">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Size:</div>
        <el-tag size="small" type="info">
          {{ sizeCategory }}
        </el-tag>
      </div>

      <!-- Multilinguality -->
      <div v-if="metadata.multilinguality">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Type:</div>
        <span class="text-gray-900 dark:text-white">
          {{ formatMetadataKey(metadata.multilinguality) }}
        </span>
      </div>

      <!-- Annotations Creators -->
      <div v-if="metadata.annotations_creators">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
          Annotations:
        </div>
        <div class="flex flex-wrap gap-1">
          <el-tag
            v-for="creator in Array.isArray(metadata.annotations_creators)
              ? metadata.annotations_creators
              : [metadata.annotations_creators]"
            :key="creator"
            size="small"
          >
            {{ formatMetadataKey(creator) }}
          </el-tag>
        </div>
      </div>

      <!-- Source Datasets -->
      <div v-if="metadata.source_datasets">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Source:</div>
        <div class="flex flex-wrap gap-1">
          <el-tag
            v-for="source in Array.isArray(metadata.source_datasets)
              ? metadata.source_datasets
              : [metadata.source_datasets]"
            :key="source"
            size="small"
            type="warning"
          >
            {{ formatMetadataKey(source) }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>
