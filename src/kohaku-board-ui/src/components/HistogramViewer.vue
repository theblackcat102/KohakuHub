<script setup>
import Plotly from "plotly.js-dist-min";

const props = defineProps({
  histogramData: Array,
  height: Number,
  currentStep: Number,
});

const emit = defineEmits(["update:currentStep"]);

const plotDiv = ref(null);
let resizeObserver = null;

const stepIndex = computed({
  get() {
    if (!props.histogramData || props.histogramData.length === 0) return 0;
    return props.histogramData.findIndex(
      (item) => item.step === props.currentStep,
    );
  },
  set(index) {
    if (props.histogramData && props.histogramData[index]) {
      emit("update:currentStep", props.histogramData[index].step);
    }
  },
});

const currentHistogram = computed(() => {
  if (!props.histogramData || props.histogramData.length === 0) return null;
  const index = stepIndex.value >= 0 ? stepIndex.value : 0;
  return props.histogramData[index];
});

watch(
  currentHistogram,
  () => {
    createPlot();
  },
  { deep: true },
);

watch(
  () => props.height,
  () => {
    createPlot();
  },
);

onMounted(() => {
  createPlot();
  setupResizeObserver();
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

function setupResizeObserver() {
  if (!plotDiv.value) return;

  resizeObserver = new ResizeObserver(() => {
    if (plotDiv.value) {
      Plotly.Plots.resize(plotDiv.value);
    }
  });

  resizeObserver.observe(plotDiv.value.parentElement || plotDiv.value);
}

function createPlot() {
  if (!plotDiv.value || !currentHistogram.value) return;

  const isDark = document.documentElement.classList.contains("dark");
  const colors = {
    text: isDark ? "#e5e7eb" : "#1f2937",
    grid: isDark ? "rgba(156, 163, 175, 0.2)" : "rgba(156, 163, 175, 0.3)",
  };

  const trace = {
    type: "histogram",
    x: currentHistogram.value.values,
    nbinsx: currentHistogram.value.bins || 30,
    marker: {
      color: isDark ? "rgba(96, 165, 250, 0.7)" : "rgba(59, 130, 246, 0.7)",
    },
  };

  const layout = {
    xaxis: { gridcolor: colors.grid, color: colors.text },
    yaxis: { gridcolor: colors.grid, color: colors.text },
    height: props.height - 100,
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { t: 10, r: 20, b: 30, l: 50 },
    autosize: true,
  };

  Plotly.react(plotDiv.value, [trace], layout, {
    responsive: true,
    displayModeBar: false,
  });
}
</script>

<template>
  <div
    class="histogram-viewer flex flex-col"
    :style="{ height: `${height}px` }"
  >
    <div v-if="currentHistogram" class="flex flex-col h-full">
      <div ref="plotDiv" class="flex-1"></div>
      <div class="mt-2 flex justify-center">
        <div class="w-1/2">
          <div
            class="text-sm text-gray-600 dark:text-gray-400 mb-2 text-center"
          >
            Step: {{ currentHistogram.step }}
          </div>
          <el-slider
            v-model="stepIndex"
            :min="0"
            :max="histogramData.length - 1"
            :marks="{ 0: 'Start', [histogramData.length - 1]: 'End' }"
          />
        </div>
      </div>
    </div>
    <el-empty v-else description="No histogram data" />
  </div>
</template>
