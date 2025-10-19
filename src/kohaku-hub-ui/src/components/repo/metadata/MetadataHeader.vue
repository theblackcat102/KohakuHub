<script setup>
import { computed } from "vue";
import {
  getLicenseName,
  getPipelineTagName,
  getLanguageName,
} from "@/utils/metadata-helpers";

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

const emit = defineEmits(["navigate-to-metadata"]);

const licenseName = computed(() => {
  return props.metadata.license ? getLicenseName(props.metadata.license) : null;
});

const languages = computed(() => {
  if (!props.metadata.language) return [];
  const langs = Array.isArray(props.metadata.language)
    ? props.metadata.language
    : [props.metadata.language];
  return langs.slice(0, 3); // Show max 3 languages in header
});

const moreLanguages = computed(() => {
  if (!props.metadata.language) return 0;
  const langs = Array.isArray(props.metadata.language)
    ? props.metadata.language
    : [props.metadata.language];
  return Math.max(0, langs.length - 3);
});

const pipelineTag = computed(() => {
  return props.metadata.pipeline_tag
    ? getPipelineTagName(props.metadata.pipeline_tag)
    : null;
});

const taskCategories = computed(() => {
  if (!props.metadata.task_categories) return [];
  const tasks = Array.isArray(props.metadata.task_categories)
    ? props.metadata.task_categories
    : [props.metadata.task_categories];
  return tasks.slice(0, 2); // Show max 2 tasks
});

const moreTasks = computed(() => {
  if (!props.metadata.task_categories) return 0;
  const tasks = Array.isArray(props.metadata.task_categories)
    ? props.metadata.task_categories
    : [props.metadata.task_categories];
  return Math.max(0, tasks.length - 2);
});

const sizeCategory = computed(() => {
  if (!props.metadata.size_categories) return null;
  const size = Array.isArray(props.metadata.size_categories)
    ? props.metadata.size_categories[0]
    : props.metadata.size_categories;
  return size;
});
</script>

<template>
  <div
    class="metadata-header bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 mb-4"
  >
    <div class="flex flex-wrap items-center gap-2">
      <!-- License -->
      <el-tag v-if="licenseName" type="info" size="small">
        <div class="i-carbon-document inline-block mr-1" />
        {{ licenseName }}
      </el-tag>

      <!-- Languages -->
      <el-tag
        v-for="lang in languages"
        :key="lang"
        type="primary"
        size="small"
        effect="plain"
      >
        <div class="i-carbon-language inline-block mr-1" />
        {{ getLanguageName(lang) }}
      </el-tag>
      <el-tag
        v-if="moreLanguages > 0"
        size="small"
        effect="plain"
        class="cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30"
        @click="emit('navigate-to-metadata')"
      >
        +{{ moreLanguages }} more
      </el-tag>

      <!-- Framework (Models) -->
      <el-tag
        v-if="repoType === 'model' && metadata.library_name"
        type="success"
        size="small"
      >
        <div class="i-carbon-cube inline-block mr-1" />
        {{ metadata.library_name }}
      </el-tag>

      <!-- Pipeline Tag (Models) -->
      <el-tag
        v-if="repoType === 'model' && pipelineTag"
        type="warning"
        size="small"
      >
        <div class="i-carbon-task inline-block mr-1" />
        {{ pipelineTag }}
      </el-tag>

      <!-- Size (Datasets) - IMPORTANT INFO -->
      <el-tag
        v-if="repoType === 'dataset' && sizeCategory"
        type="danger"
        size="small"
      >
        <div class="i-carbon-data-volume inline-block mr-1" />
        {{ sizeCategory }}
      </el-tag>

      <!-- Task Categories (Datasets) -->
      <el-tag
        v-for="task in taskCategories"
        :key="task"
        v-if="repoType === 'dataset'"
        type="success"
        size="small"
      >
        <div class="i-carbon-checkbox-checked inline-block mr-1" />
        {{ task }}
      </el-tag>
      <el-tag
        v-if="moreTasks > 0"
        size="small"
        effect="plain"
        class="cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/30"
        @click="emit('navigate-to-metadata')"
      >
        +{{ moreTasks }} more
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.metadata-header {
  border: 1px solid var(--el-border-color-lighter);
}
</style>
