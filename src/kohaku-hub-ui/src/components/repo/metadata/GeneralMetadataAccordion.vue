<script setup>
import { computed } from "vue";
import { formatMetadataKey } from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const metadataCount = computed(() => {
  return Object.keys(props.metadata).length;
});

const sortedMetadata = computed(() => {
  return Object.entries(props.metadata).sort(([a], [b]) => a.localeCompare(b));
});

function formatValue(value) {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function isComplexValue(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
</script>

<template>
  <div class="card">
    <el-collapse>
      <el-collapse-item>
        <template #title>
          <div class="flex items-center gap-2 text-gray-900 dark:text-white">
            <div class="i-carbon-information text-base" />
            <span class="font-semibold">Additional Metadata</span>
            <el-tag size="small" type="info">{{ metadataCount }}</el-tag>
          </div>
        </template>

        <div class="space-y-3 text-sm">
          <div
            v-for="[key, value] in sortedMetadata"
            :key="key"
            class="metadata-row"
          >
            <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
              {{ formatMetadataKey(key) }}:
            </div>
            <div v-if="isComplexValue(value)" class="ml-2">
              <pre
                class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto"
              ><code class="text-gray-900 dark:text-gray-100">{{ formatValue(value) }}</code></pre>
            </div>
            <div v-else class="ml-2 text-gray-900 dark:text-white">
              {{ formatValue(value) }}
            </div>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.metadata-row {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(128, 128, 128, 0.1);
}

.metadata-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

pre {
  margin: 0;
}
</style>
