<script setup>
import { computed } from "vue";
import { getPipelineTagName } from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const pipelineTagName = computed(() => {
  return props.metadata.pipeline_tag
    ? getPipelineTagName(props.metadata.pipeline_tag)
    : null;
});

const libraryIcon = computed(() => {
  const lib = props.metadata.library_name?.toLowerCase();
  const iconMap = {
    transformers: "i-carbon-model",
    diffusers: "i-carbon-image",
    timm: "i-carbon-image-reference",
    peft: "i-carbon-connect",
    "sentence-transformers": "i-carbon-text-align-justify",
  };
  return iconMap[lib] || "i-carbon-cube";
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">Framework</h3>
    <div class="space-y-3 text-sm">
      <div v-if="metadata.library_name" class="flex items-center gap-2">
        <div
          :class="libraryIcon"
          class="text-base text-purple-500 dark:text-purple-400"
        />
        <span class="font-medium text-gray-900 dark:text-white">
          {{ metadata.library_name }}
        </span>
      </div>

      <div v-if="pipelineTagName">
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">Task:</div>
        <el-tag type="success" size="small">
          {{ pipelineTagName }}
        </el-tag>
      </div>
    </div>
  </div>
</template>
