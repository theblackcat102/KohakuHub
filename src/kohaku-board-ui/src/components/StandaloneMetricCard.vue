<script setup>
const props = defineProps({
  metricName: String,
  metricType: String, // 'media', 'table', 'histogram'
  runs: Array, // [{id, name, color}]
  project: String,
});

const currentStep = ref(0);
</script>

<template>
  <div class="standalone-metric-card">
    <h3 class="text-lg font-bold mb-4">{{ metricName }}</h3>

    <div class="grid grid-cols-1 gap-4">
      <div
        v-for="run in runs"
        :key="run.id"
        class="sub-card p-4 border rounded-lg bg-white dark:bg-gray-800"
      >
        <h4 class="text-md font-semibold mb-2 flex items-center gap-2">
          <span
            class="w-3 h-3 rounded-full"
            :style="{ backgroundColor: run.color }"
          ></span>
          {{ run.name }}
        </h4>

        <!-- Media Viewer -->
        <div v-if="metricType === 'media'" class="media-viewer">
          <iframe
            :src="`/experiments/${run.id}?media=${encodeURIComponent(metricName)}&step=${currentStep}`"
            class="w-full h-96 border-0"
            sandbox="allow-same-origin"
          />
        </div>

        <!-- Table Viewer -->
        <div v-else-if="metricType === 'table'" class="table-viewer">
          <iframe
            :src="`/experiments/${run.id}?table=${encodeURIComponent(metricName)}&step=${currentStep}`"
            class="w-full h-96 border-0"
            sandbox="allow-same-origin"
          />
        </div>

        <!-- Histogram Viewer -->
        <div v-else-if="metricType === 'histogram'" class="histogram-viewer">
          <iframe
            :src="`/experiments/${run.id}?histogram=${encodeURIComponent(metricName)}&step=${currentStep}`"
            class="w-full h-96 border-0"
            sandbox="allow-same-origin"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.standalone-metric-card {
  background: #f9f9f9;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

:deep(.dark) .standalone-metric-card {
  background: #2a2a2a;
}

.sub-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
</style>
