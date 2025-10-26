<script setup>
import { VueDraggable } from "vue-draggable-plus";
import ConfigurableChartCard from "@/components/ConfigurableChartCard.vue";
import { useAnimationPreference } from "@/composables/useAnimationPreference";

const route = useRoute();
const { animationsEnabled } = useAnimationPreference();
const metricDataCache = ref({});
const availableMetrics = ref([]);

const tabs = ref([{ name: "Metrics", cards: [] }]);
const activeTab = ref("Metrics");
const nextCardId = ref(1);
const isEditingTabs = ref(false);
const isUpdating = ref(false);
const showAddTabDialog = ref(false);
const newTabName = ref("");

const storageKey = computed(() => `experiment-layout-${route.params.id}`);

onMounted(async () => {
  try {
    const experimentId = route.params.id;

    // Fetch summary (just metric names)
    const summaryResponse = await fetch(
      `/api/experiments/${experimentId}/summary`,
    );
    const summary = await summaryResponse.json();
    availableMetrics.value = summary.available_data.scalars;

    // Add computed time metrics (will be calculated after fetching timestamp)
    // These are not in the backend, but calculated on frontend
    if (availableMetrics.value.includes("timestamp")) {
      availableMetrics.value.push("walltime");
      availableMetrics.value.push("relative_walltime");
    }

    // Try to load saved layout
    const saved = localStorage.getItem(storageKey.value);
    if (saved) {
      const layout = JSON.parse(saved);
      tabs.value = layout.tabs;
      activeTab.value = layout.activeTab;
      nextCardId.value = layout.nextCardId;
    } else {
      // Default: one card per scalar metric + examples of other types
      const cards = [];
      let cardId = 1;

      // Scalar metrics (exclude step/global_step from y-axis, use as x-axis only)
      for (const metric of summary.available_data.scalars) {
        if (metric !== "step" && metric !== "global_step") {
          cards.push({
            id: `card-${cardId++}`,
            config: {
              type: "line",
              title: metric,
              widthPercent: 33,
              height: 400,
              xMetric: "step", // Will be updated to global_step if used
              yMetrics: [metric],
            },
          });
        }
      }

      // Add media example
      if (summary.available_data.media.length > 0) {
        cards.push({
          id: `card-${cardId++}`,
          config: {
            type: "media",
            title: summary.available_data.media[0],
            widthPercent: 33,
            height: 400,
            mediaName: summary.available_data.media[0],
            currentStep: 0,
          },
        });
      }

      // Add histogram example
      if (summary.available_data.histograms.length > 0) {
        cards.push({
          id: `card-${cardId++}`,
          config: {
            type: "histogram",
            title: summary.available_data.histograms[0],
            widthPercent: 33,
            height: 400,
            histogramName: summary.available_data.histograms[0],
            currentStep: 0,
          },
        });
      }

      // Add table example
      if (summary.available_data.tables.length > 0) {
        cards.push({
          id: `card-${cardId++}`,
          config: {
            type: "table",
            title: summary.available_data.tables[0],
            widthPercent: 50,
            height: 400,
            tableName: summary.available_data.tables[0],
            currentStep: 0,
          },
        });
      }

      tabs.value[0].cards = cards;
      nextCardId.value = cardId;
    }

    // Fetch all metrics needed by visible cards
    await fetchMetricsForTab();

    // Determine default x-axis (prefer global_step if it's used, otherwise step)
    await determineDefaultXAxis();
  } catch (error) {
    console.error("Failed to load experiment:", error);
  }
});

async function determineDefaultXAxis() {
  // Check if global_step has any non-zero values
  try {
    const response = await fetch(
      `/api/experiments/${route.params.id}/scalars/global_step`,
    );
    const result = await response.json();

    // Check if any global_step value is non-zero
    const hasNonZeroGlobalStep = result.data.some(
      (item) => item.value !== 0 && item.value !== null,
    );

    // Update all cards to use global_step if it's being used
    if (hasNonZeroGlobalStep) {
      for (const tab of tabs.value) {
        for (const card of tab.cards) {
          if (card.config.type === "line" || !card.config.type) {
            if (card.config.xMetric === "step") {
              card.config.xMetric = "global_step";
            }
          }
        }
      }
      saveLayout();
    }
  } catch (error) {
    console.error("Failed to determine default x-axis:", error);
  }
}

async function fetchMetricsForTab() {
  const tab = tabs.value.find((t) => t.name === activeTab.value);
  if (!tab) return;

  const neededMetrics = new Set();
  for (const card of tab.cards) {
    // Only fetch for line plot cards
    if (card.config.type === "line" || !card.config.type) {
      if (card.config.xMetric) neededMetrics.add(card.config.xMetric);
      if (card.config.yMetrics) {
        for (const yMetric of card.config.yMetrics) {
          neededMetrics.add(yMetric);
        }
      }
    }
  }

  // Fetch missing metrics
  for (const metric of neededMetrics) {
    if (!metricDataCache.value[metric]) {
      try {
        const response = await fetch(
          `/api/experiments/${route.params.id}/scalars/${metric}`,
        );
        const result = await response.json();

        // Convert step-value pairs to sparse array
        const sparseArray = new Array(
          result.data[result.data.length - 1]?.step + 1 || 0,
        ).fill(null);
        for (const item of result.data) {
          sparseArray[item.step] = item.value;
        }

        metricDataCache.value[metric] = sparseArray;

        // Also store timestamp data if available
        if (result.data[0]?.timestamp) {
          const timestampArray = new Array(sparseArray.length).fill(null);
          for (const item of result.data) {
            timestampArray[item.step] = item.timestamp;
          }
          metricDataCache.value[`${metric}_timestamp`] = timestampArray;
        }
      } catch (error) {
        console.error(`Failed to fetch metric ${metric}:`, error);
      }
    }
  }

  // Calculate walltime and relative_walltime from timestamps
  if (metricDataCache.value.timestamp) {
    const timestamps = metricDataCache.value.timestamp;
    const walltime = [];
    const relativeWalltime = [];
    let startTime = null;

    for (let i = 0; i < timestamps.length; i++) {
      if (timestamps[i]) {
        const ts = new Date(timestamps[i]).getTime() / 1000; // Convert to seconds
        walltime[i] = ts;

        if (startTime === null) {
          startTime = ts;
          relativeWalltime[i] = 0;
        } else {
          relativeWalltime[i] = ts - startTime;
        }
      } else {
        walltime[i] = null;
        relativeWalltime[i] = null;
      }
    }

    metricDataCache.value.walltime = walltime;
    metricDataCache.value.relative_walltime = relativeWalltime;
  }
}

const sparseData = computed(() => {
  const data = { time: metricDataCache.value.step || [] };
  for (const [key, values] of Object.entries(metricDataCache.value)) {
    data[key] = values;
  }
  return data;
});

const currentTabCards = computed({
  get() {
    const tab = tabs.value.find((t) => t.name === activeTab.value);
    return tab ? tab.cards : [];
  },
  set(newCards) {
    const tab = tabs.value.find((t) => t.name === activeTab.value);
    if (tab) {
      tab.cards = newCards;
      saveLayout();
    }
  },
});

function saveLayout() {
  const layout = {
    tabs: tabs.value,
    activeTab: activeTab.value,
    nextCardId: nextCardId.value,
  };
  localStorage.setItem(storageKey.value, JSON.stringify(layout));
}

function addCard() {
  const tab = tabs.value.find((t) => t.name === activeTab.value);
  if (!tab) return;

  const newCard = {
    id: `card-${nextCardId.value++}`,
    config: {
      title: `Chart ${nextCardId.value - 1}`,
      widthPercent: 33,
      height: 400,
      xMetric: "step",
      yMetrics: [],
    },
  };
  tab.cards.push(newCard);
  saveLayout();
}

function addTab() {
  showAddTabDialog.value = true;
  newTabName.value = "";
}

function confirmAddTab() {
  if (newTabName.value.trim()) {
    tabs.value.push({ name: newTabName.value.trim(), cards: [] });
    saveLayout();
    showAddTabDialog.value = false;
    newTabName.value = "";
  }
}

function removeTab(tabName) {
  if (tabs.value.length <= 1) {
    ElMessage.warning("Cannot remove the last tab");
    return;
  }
  tabs.value = tabs.value.filter((t) => t.name !== tabName);
  if (activeTab.value === tabName) {
    activeTab.value = tabs.value[0].name;
  }
  saveLayout();
}

function calculateRows(cards) {
  const rows = [];
  let currentRow = [];
  let rowWidth = 0;

  for (let i = 0; i < cards.length; i++) {
    const w = cards[i].config.widthPercent || 100;
    if (rowWidth > 0 && rowWidth + w > 102) {
      rows.push([...currentRow]);
      currentRow = [];
      rowWidth = 0;
    }
    currentRow.push(i);
    rowWidth += w;
  }
  if (currentRow.length > 0) rows.push(currentRow);
  return rows;
}

function updateCard({ id, config }) {
  if (!config) return;

  const currentTab = tabs.value.find((t) => t.name === activeTab.value);
  if (!currentTab) return;

  const cardIndex = currentTab.cards.findIndex((c) => c.id === id);
  if (cardIndex === -1) return;

  const oldConfig = currentTab.cards[cardIndex].config;
  const heightChanged = oldConfig.height !== config.height;
  const widthChanged = oldConfig.widthPercent !== config.widthPercent;

  currentTab.cards[cardIndex].config = config;

  if (isUpdating.value) return;
  isUpdating.value = true;

  try {
    if (heightChanged && !widthChanged) {
      const rows = calculateRows(currentTab.cards);
      const currentRow = rows.find((row) => row.includes(cardIndex));

      if (currentRow && currentRow.length > 1) {
        for (const idx of currentRow) {
          if (idx !== cardIndex) {
            currentTab.cards[idx].config = {
              ...currentTab.cards[idx].config,
              height: config.height,
            };
          }
        }
      }
    } else if (widthChanged) {
      const rows = calculateRows(currentTab.cards);

      // Sync all rows (because width change can cause passive row wrapping)
      for (const row of rows) {
        if (row.length > 1) {
          // Determine the target height for this row
          // Priority: use height of existing cards (excluding the actively resized one if in this row)
          const isActiveCardInRow = row.includes(cardIndex);

          let targetHeight = null;

          // First, try to find height from other cards (not the actively resized one)
          const otherCards = row.filter((idx) => idx !== cardIndex);
          if (otherCards.length > 0) {
            // Use the first other card's height as the row's target height
            targetHeight = currentTab.cards[otherCards[0]].config.height;
          } else if (isActiveCardInRow) {
            // If this row only has the actively resized card, use its current height
            targetHeight = currentTab.cards[cardIndex].config.height;
          }

          if (targetHeight !== null) {
            // Sync all cards in this row to the target height
            for (const idx of row) {
              if (currentTab.cards[idx].config.height !== targetHeight) {
                console.log(
                  `[Card ${idx}] Width change caused row wrap, syncing to row height: ${targetHeight}px`,
                );
                currentTab.cards[idx].config = {
                  ...currentTab.cards[idx].config,
                  height: targetHeight,
                };
              }
            }
          }
        }
      }
    }
  } finally {
    nextTick(() => {
      isUpdating.value = false;
      saveLayout();
    });
  }
}

function removeCard(id) {
  const tab = tabs.value.find((t) => t.name === activeTab.value);
  if (tab) {
    tab.cards = tab.cards.filter((c) => c.id !== id);
    saveLayout();
  }
}

function onDragEnd(evt) {
  console.log("[DragEnd] Syncing heights after drag", evt);
  const currentTab = tabs.value.find((t) => t.name === activeTab.value);
  if (!currentTab) return;

  const draggedIndex = evt.newIndex;
  const oldIndex = evt.oldIndex;

  if (draggedIndex === undefined || oldIndex === undefined) {
    saveLayout();
    return;
  }

  // Calculate rows after the drag
  const newRows = calculateRows(currentTab.cards);

  // Sync ALL rows that have multiple cards
  for (const row of newRows) {
    if (row.length > 1) {
      // Find the "dominant" height: the most common height among cards in this row
      const heightCounts = {};

      for (const idx of row) {
        const h = currentTab.cards[idx].config.height;
        heightCounts[h] = (heightCounts[h] || 0) + 1;
      }

      // Find the most common height (the row's "original" height)
      let dominantHeight = null;
      let maxCount = 0;

      for (const [height, count] of Object.entries(heightCounts)) {
        if (count > maxCount) {
          maxCount = count;
          dominantHeight = parseInt(height);
        }
      }

      if (dominantHeight !== null) {
        // Sync ALL cards in this row to the dominant height
        for (const idx of row) {
          if (currentTab.cards[idx].config.height !== dominantHeight) {
            const cardLabel = idx === draggedIndex ? "(dragged)" : "(in-row)";
            console.log(
              `[DragEnd] Card ${idx} ${cardLabel} syncing to dominant row height: ${dominantHeight}px`,
            );
            currentTab.cards[idx].config = {
              ...currentTab.cards[idx].config,
              height: dominantHeight,
            };
          }
        }
      }
    }
  }

  saveLayout();
}

watch(activeTab, () => {
  fetchMetricsForTab();
  saveLayout();
});
</script>

<template>
  <div class="container-main">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-3xl font-bold">Experiment: {{ route.params.id }}</h1>
      <div class="flex gap-2">
        <el-button type="primary" size="small" @click="addCard"
          >Add Chart</el-button
        >
        <el-button size="small" @click="addTab">Add Tab</el-button>
        <el-button size="small" @click="isEditingTabs = !isEditingTabs">
          {{ isEditingTabs ? "Done Editing" : "Edit Tabs" }}
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="card">
      <el-tab-pane
        v-for="tab in tabs"
        :key="tab.name"
        :label="tab.name"
        :name="tab.name"
      >
        <template #label>
          <span>{{ tab.name }}</span>
          <el-button
            v-if="isEditingTabs && tabs.length > 1"
            icon="Close"
            size="small"
            text
            type="danger"
            @click.stop="removeTab(tab.name)"
            class="ml-2"
          />
        </template>
      </el-tab-pane>
    </el-tabs>

    <VueDraggable
      v-model="currentTabCards"
      :animation="animationsEnabled ? 200 : 0"
      handle=".card-drag-handle"
      class="flex flex-wrap gap-4 mt-4"
      @end="onDragEnd"
    >
      <ConfigurableChartCard
        v-for="card in currentTabCards"
        :key="card.id"
        :card-id="card.id"
        :experiment-id="route.params.id"
        :sparse-data="sparseData"
        :available-metrics="availableMetrics"
        :initial-config="card.config"
        @update:config="updateCard"
        @remove="removeCard(card.id)"
      />
    </VueDraggable>

    <el-empty
      v-if="currentTabCards.length === 0"
      description="No charts in this tab"
    >
      <el-button type="primary" @click="addCard">Add Chart</el-button>
    </el-empty>

    <el-dialog v-model="showAddTabDialog" title="Add Tab" width="400px">
      <el-form @submit.prevent="confirmAddTab">
        <el-form-item label="Tab Name">
          <el-input
            v-model="newTabName"
            placeholder="Enter tab name"
            @keyup.enter="confirmAddTab"
            autofocus
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddTabDialog = false">Cancel</el-button>
        <el-button type="primary" @click="confirmAddTab">Add</el-button>
      </template>
    </el-dialog>
  </div>
</template>
