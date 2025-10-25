<script setup>
import LinePlot from "./LinePlot.vue";
import MediaViewer from "./MediaViewer.vue";
import HistogramViewer from "./HistogramViewer.vue";
import TableViewer from "./TableViewer.vue";

const props = defineProps({
  cardId: String,
  sparseData: Object,
  availableMetrics: Array,
  initialConfig: Object,
  experimentId: String,
});

const emit = defineEmits(["update:config", "remove"]);

console.log(`[${props.cardId}] Component created`);

// Direct reference to props
const cfg = props.initialConfig;
const localHeight = ref(cfg.height);
const localWidth = ref(cfg.widthPercent);
const isEditingTitle = ref(false);
const editedTitle = ref(cfg.title);
const isResizingWidth = ref(false);
const previewWidth = ref(null);
const showSettings = ref(false);
const plotRef = ref(null);

// Sync when parent updates (only if actually different)
watch(
  () => props.initialConfig.height,
  (h, oldH) => {
    if (h !== undefined && h !== localHeight.value) {
      console.log(
        `[${props.cardId}] Height prop changed: ${localHeight.value} → ${h}`,
      );
      localHeight.value = h;
    }
  },
);
watch(
  () => props.initialConfig.widthPercent,
  (w, oldW) => {
    if (w !== undefined && w !== localWidth.value) {
      console.log(
        `[${props.cardId}] Width prop changed: ${localWidth.value} → ${w}`,
      );
      localWidth.value = w;
    }
  },
);

onMounted(() => {
  console.log(`[${props.cardId}] Component mounted`);
});

onUnmounted(() => {
  console.log(`[${props.cardId}] Component unmounted`);
});

onUpdated(() => {
  console.log(`[${props.cardId}] Component updated/re-rendered`);
});

const cardType = computed(() => props.initialConfig.type || "line");
const mediaData = ref(null);
const histogramData = ref(null);
const tableData = ref(null);
const currentStepIndex = ref(0);

// Fetch non-scalar data based on type
watch(
  cardType,
  async (type) => {
    if (type === "media" && props.initialConfig.mediaName) {
      const res = await fetch(
        `/api/experiments/${props.experimentId}/media/${props.initialConfig.mediaName}`,
      );
      const data = await res.json();
      mediaData.value = data.data;
    } else if (type === "histogram" && props.initialConfig.histogramName) {
      const res = await fetch(
        `/api/experiments/${props.experimentId}/histograms/${props.initialConfig.histogramName}`,
      );
      const data = await res.json();
      histogramData.value = data.data;
    } else if (type === "table" && props.initialConfig.tableName) {
      const res = await fetch(
        `/api/experiments/${props.experimentId}/tables/${props.initialConfig.tableName}`,
      );
      const data = await res.json();
      tableData.value = data.data;
    }
  },
  { immediate: true },
);

const processedChartData = computed(() => {
  const config = props.initialConfig;
  console.log(
    `[${props.cardId}] processedChartData computed, type: ${cardType.value}`,
  );

  if (cardType.value !== "line") return [];
  if (!config.xMetric || !config.yMetrics || config.yMetrics.length === 0)
    return [];

  const xData = props.sparseData[config.xMetric];
  if (!xData) return [];

  return config.yMetrics
    .map((yMetric) => {
      const yData = props.sparseData[yMetric];
      if (!yData) return null;

      const x = [];
      const y = [];
      let lastXValue = null;

      for (let i = 0; i < xData.length; i++) {
        const xVal = xData[i];
        const yVal = yData[i];

        if (xVal !== null) lastXValue = xVal;
        if (yVal !== null && lastXValue !== null) {
          x.push(lastXValue);
          y.push(yVal);
        }
      }

      return { name: yMetric, x, y };
    })
    .filter((d) => d !== null);
});

function saveTitle() {
  const newConfig = { ...props.initialConfig, title: editedTitle.value };
  isEditingTitle.value = false;
  emit("update:config", { id: props.cardId, config: newConfig });
}

function emitConfig(updates = {}) {
  const newConfig = { ...props.initialConfig, ...updates };
  console.log(`[${props.cardId}] emitConfig:`, updates, "→", newConfig);
  emit("update:config", { id: props.cardId, config: newConfig });
}

function resetView() {
  if (plotRef.value?.resetView) {
    plotRef.value.resetView();
  }
}

function exportPNG() {
  if (plotRef.value?.exportPNG) {
    plotRef.value.exportPNG();
  }
}

const plotConfig = computed(() => plotRef.value?.plotConfig || null);

function startResizeBottom(e) {
  e.preventDefault();
  e.stopPropagation();
  const startY = e.clientY;
  const startHeight = props.initialConfig.height;
  let tempHeight = startHeight;

  const onMove = (e) => {
    tempHeight = Math.max(
      200,
      Math.min(1000, startHeight + (e.clientY - startY)),
    );
    localHeight.value = tempHeight;
  };

  const onUp = () => {
    emitConfig({ height: tempHeight });
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function startResizeRight(e) {
  e.preventDefault();
  e.stopPropagation();

  isResizingWidth.value = true;
  const startX = e.clientX;
  const cardEl = e.target.closest(".chart-card-wrapper");
  if (!cardEl) return;

  const parentWidth =
    cardEl.parentElement?.getBoundingClientRect().width || 1000;
  const startWidth = cardEl.getBoundingClientRect().width;

  // Initialize preview with current width
  previewWidth.value = props.initialConfig.widthPercent;

  const onMove = (e) => {
    const deltaX = e.clientX - startX;
    const newWidth = startWidth + deltaX;
    const ratioPercent = (newWidth / parentWidth) * 100;

    const snaps = [
      { p: 12.5, l: "1/8" },
      { p: 16, l: "1/6" },
      { p: 20, l: "1/5" },
      { p: 25, l: "1/4" },
      { p: 33, l: "1/3" },
      { p: 50, l: "1/2" },
      { p: 66, l: "2/3" },
      { p: 100, l: "Full" },
    ];

    let closest = snaps[0];
    let minDiff = Math.abs(ratioPercent - snaps[0].p);

    for (const snap of snaps) {
      const diff = Math.abs(ratioPercent - snap.p);
      if (diff < minDiff) {
        minDiff = diff;
        closest = snap;
      }
    }

    previewWidth.value = closest.p;
    localWidth.value = closest.p;
  };

  const onUp = () => {
    if (
      previewWidth.value !== null &&
      previewWidth.value !== props.initialConfig.widthPercent
    ) {
      console.log(
        `[${props.cardId}] Width actually changed, emitting with height to maintain size`,
      );
      emitConfig({ widthPercent: localWidth.value, height: localHeight.value });
    } else {
      console.log(
        `[${props.cardId}] Width unchanged (${previewWidth.value}), not emitting`,
      );
    }
    isResizingWidth.value = false;
    previewWidth.value = null;
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}
</script>

<template>
  <div
    class="chart-card-wrapper"
    :class="{ 'resizing-width': isResizingWidth }"
    :style="{
      flex: `0 0 calc(${localWidth || 100}% - 16px)`,
      maxWidth: `calc(${localWidth || 100}% - 16px)`,
    }"
  >
    <div
      v-if="isResizingWidth"
      class="width-preview-overlay"
      :style="{
        width: `calc(${previewWidth}% - 16px)`,
      }"
    >
      <div class="width-preview-text">
        {{
          previewWidth === 100
            ? "Full"
            : previewWidth === 66
              ? "2/3"
              : previewWidth === 50
                ? "1/2"
                : previewWidth === 33
                  ? "1/3"
                  : previewWidth === 25
                    ? "1/4"
                    : previewWidth === 20
                      ? "1/5"
                      : previewWidth === 16
                        ? "1/6"
                        : previewWidth === 12.5
                          ? "1/8"
                          : previewWidth + "%"
        }}
      </div>
    </div>
    <el-card :body-style="{ padding: '12px' }">
      <template #header>
        <div class="space-y-2">
          <div class="flex items-center gap-2 card-drag-handle cursor-move">
            <i class="i-ep-rank text-gray-400"></i>
            <span
              v-if="!isEditingTitle"
              class="font-semibold truncate flex-1 cursor-pointer"
              :title="props.initialConfig.title"
              @dblclick="isEditingTitle = true"
            >
              {{ props.initialConfig.title }}
            </span>
            <el-input
              v-else
              v-model="editedTitle"
              size="small"
              class="flex-1"
              @keyup.enter="saveTitle"
              @keyup.esc="isEditingTitle = false"
              @click.stop
            />
            <el-button
              v-if="!isEditingTitle"
              icon="Edit"
              size="small"
              text
              @click.stop="isEditingTitle = true"
            />
            <el-button
              v-else
              size="small"
              type="primary"
              @click.stop="saveTitle"
              >Save</el-button
            >
            <el-button
              v-if="isEditingTitle"
              size="small"
              @click.stop="isEditingTitle = false"
              >Cancel</el-button
            >
          </div>
          <div
            class="flex gap-0.5 border-t border-gray-100 dark:border-gray-700 pt-2"
          >
            <el-button size="small" @click.stop="resetView" title="Reset View">
              <i class="i-ep-refresh-left"></i>
            </el-button>
            <el-button size="small" @click.stop="exportPNG" title="Export PNG">
              <i class="i-ep-download"></i>
            </el-button>
            <el-button
              size="small"
              @click.stop="showSettings = true"
              title="Settings"
            >
              <i class="i-ep-setting"></i>
            </el-button>
            <el-button
              size="small"
              type="danger"
              text
              @click.stop="$emit('remove')"
              title="Remove Card"
            >
              <i class="i-ep-delete"></i>
            </el-button>
          </div>
        </div>
      </template>

      <div class="plot-container" :style="{ height: `${localHeight}px` }">
        <LinePlot
          v-if="cardType === 'line' && processedChartData.length > 0"
          ref="plotRef"
          :data="processedChartData"
          :xaxis="props.initialConfig.xMetric"
          yaxis="Value"
          :height="localHeight"
          :hide-toolbar="true"
        />
        <MediaViewer
          v-else-if="cardType === 'media' && mediaData"
          :media-data="mediaData"
          :height="localHeight"
          :current-step="props.initialConfig.currentStep || 0"
          :card-id="props.cardId"
          @update:current-step="(s) => emitConfig({ currentStep: s })"
        />
        <HistogramViewer
          v-else-if="cardType === 'histogram' && histogramData"
          :histogram-data="histogramData"
          :height="localHeight"
          :current-step="props.initialConfig.currentStep || 0"
          :card-id="props.cardId"
          @update:current-step="(s) => emitConfig({ currentStep: s })"
        />
        <TableViewer
          v-else-if="cardType === 'table' && tableData"
          :table-data="tableData"
          :height="localHeight"
          :current-step="props.initialConfig.currentStep || 0"
          :card-id="props.cardId"
          @update:current-step="(s) => emitConfig({ currentStep: s })"
        />
        <el-empty v-else description="Select metrics" />
      </div>
    </el-card>

    <div
      @mousedown.stop.prevent="startResizeBottom"
      class="resize-handle resize-handle-bottom"
      title="Drag to resize height"
    ></div>
    <div
      @mousedown.stop.prevent="startResizeRight"
      class="resize-handle resize-handle-right"
      title="Drag to resize width"
    ></div>
    <div
      @mousedown.stop.prevent="startResizeRight"
      class="resize-handle resize-handle-corner"
      title="Drag to resize width"
    ></div>

    <el-dialog
      v-model="showSettings"
      title="Chart Settings"
      width="700px"
      @click.stop
      append-to-body
    >
      <el-form label-width="150px">
        <el-divider content-position="left">Data Selection</el-divider>
        <el-form-item label="X-Axis">
          <el-select
            :model-value="props.initialConfig.xMetric"
            @change="(v) => emitConfig({ xMetric: v })"
            class="w-full"
          >
            <el-option
              v-for="m in availableMetrics"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Y-Axis">
          <el-select
            :model-value="props.initialConfig.yMetrics"
            @change="(v) => emitConfig({ yMetrics: v })"
            multiple
            collapse-tags
            collapse-tags-tooltip
            class="w-full"
            placeholder="Select metrics"
          >
            <el-option
              v-for="m in availableMetrics.filter(
                (x) => x !== props.initialConfig.xMetric,
              )"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
        </el-form-item>

        <template v-if="plotConfig">
          <el-divider content-position="left">Axis Range</el-divider>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="X-Axis Auto">
                <el-switch v-model="plotConfig.xRange.auto" />
              </el-form-item>
              <el-row v-if="!plotConfig.xRange.auto" :gutter="8">
                <el-col :span="12">
                  <el-input
                    v-model.number="plotConfig.xRange.min"
                    placeholder="Min"
                    size="small"
                    type="number"
                  />
                </el-col>
                <el-col :span="12">
                  <el-input
                    v-model.number="plotConfig.xRange.max"
                    placeholder="Max"
                    size="small"
                    type="number"
                  />
                </el-col>
              </el-row>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Y-Axis Auto">
                <el-switch v-model="plotConfig.yRange.auto" />
              </el-form-item>
              <el-row v-if="!plotConfig.yRange.auto" :gutter="8">
                <el-col :span="12">
                  <el-input
                    v-model.number="plotConfig.yRange.min"
                    placeholder="Min"
                    size="small"
                    type="number"
                    step="0.1"
                  />
                </el-col>
                <el-col :span="12">
                  <el-input
                    v-model.number="plotConfig.yRange.max"
                    placeholder="Max"
                    size="small"
                    type="number"
                    step="0.1"
                  />
                </el-col>
              </el-row>
            </el-col>
          </el-row>

          <el-divider content-position="left">Smoothing</el-divider>
          <el-form-item label="Mode">
            <el-select v-model="plotConfig.smoothingMode" class="w-full">
              <el-option label="Disabled" value="disabled" />
              <el-option label="EMA (Exponential Moving Average)" value="ema" />
              <el-option label="MA (Moving Average)" value="ma" />
              <el-option label="Gaussian" value="gaussian" />
            </el-select>
          </el-form-item>
          <el-form-item
            v-if="plotConfig.smoothingMode !== 'disabled'"
            :label="
              plotConfig.smoothingMode === 'ema'
                ? 'Decay (0-1)'
                : plotConfig.smoothingMode === 'ma'
                  ? 'Window Size'
                  : 'Kernel Size'
            "
          >
            <el-input-number
              v-model="plotConfig.smoothingValue"
              :min="plotConfig.smoothingMode === 'ema' ? 0 : 1"
              :max="plotConfig.smoothingMode === 'ema' ? 1 : 1000"
              :step="plotConfig.smoothingMode === 'ema' ? 0.01 : 1"
              class="w-full"
            />
          </el-form-item>
          <el-form-item
            v-if="plotConfig.smoothingMode !== 'disabled'"
            label="Show Original"
          >
            <el-switch v-model="plotConfig.showOriginal" />
          </el-form-item>

          <el-divider content-position="left">Display Options</el-divider>
          <el-form-item label="Downsample Rate">
            <el-input-number
              v-model="plotConfig.downsampleRate"
              :min="1"
              :max="100"
              class="w-full"
            />
          </el-form-item>
          <el-form-item label="Line Width">
            <el-slider
              v-model="plotConfig.lineWidth"
              :min="0.5"
              :max="5"
              :step="0.5"
            />
          </el-form-item>
          <el-form-item label="Show Markers">
            <el-switch v-model="plotConfig.showMarkers" />
          </el-form-item>
        </template>
      </el-form>
    </el-dialog>
  </div>
</template>

<style scoped>
.chart-card-wrapper {
  position: relative;
  height: 100%;
}

@media (max-width: 900px) {
  .chart-card-wrapper {
    flex: 0 0 100% !important;
    max-width: 100% !important;
  }

  .chart-card-wrapper :deep(.el-card__body) {
    padding: 8px !important;
  }
}

.resize-handle {
  position: absolute;
  background: transparent;
  transition: background 0.2s;
}

.resize-handle:hover {
  background: rgba(64, 158, 255, 0.15);
}

.resize-handle-bottom {
  bottom: 0;
  left: 0;
  right: 0;
  height: 6px;
  cursor: ns-resize;
  z-index: 10;
}

.resize-handle-right {
  top: 0;
  right: 0;
  bottom: 0;
  width: 6px;
  cursor: ew-resize;
  z-index: 10;
}

.resize-handle-corner {
  bottom: 0;
  right: 0;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  z-index: 10;
}

.resize-handle-corner::after {
  content: "";
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 0 12px 12px;
  border-color: transparent transparent rgba(64, 158, 255, 0.4) transparent;
}

.resizing-width {
  opacity: 0.7;
}

.plot-container {
  position: relative;
  width: 100%;
}

.width-preview-overlay {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  background: rgba(64, 158, 255, 0.1);
  border: 3px dashed rgba(64, 158, 255, 0.5);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  min-width: 100%;
}

.width-preview-text {
  background: rgba(64, 158, 255, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 16px;
}
</style>
