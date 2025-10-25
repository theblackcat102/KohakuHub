<script setup>
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import ConfigurableChartCard from "@/components/ConfigurableChartCard.vue";

const route = useRoute();
const sparseData = ref(null);
const availableMetrics = ref([]);
const cards = ref([]);
const nextCardId = ref(1);
const loading = ref(true);

onMounted(async () => {
  try {
    const experimentId = route.params.id || "exp-001";
    const response = await fetch(
      `/api/experiments/${experimentId}/sparse-metrics?total_events=100000`,
    );
    const result = await response.json();

    sparseData.value = result.data;
    availableMetrics.value = result.available_metrics;

    cards.value = [
      {
        id: "card-1",
        config: {
          title: "Training Loss",
          width: 12,
          height: 400,
          xMetric: "step",
          yMetrics: ["train_loss"],
        },
      },
      {
        id: "card-2",
        config: {
          title: "Training & Validation",
          width: 12,
          height: 400,
          xMetric: "step",
          yMetrics: ["train_loss", "val_loss"],
        },
      },
    ];
    nextCardId.value = 3;
  } catch (error) {
    console.error("Failed to fetch sparse metrics:", error);
  } finally {
    loading.value = false;
  }
});

function addCard() {
  const newCard = {
    id: `card-${nextCardId.value++}`,
    config: {
      title: `Chart ${nextCardId.value - 1}`,
      width: 12,
      height: 400,
      xMetric: availableMetrics.value[0] || "step",
      yMetrics: [],
    },
  };
  cards.value.push(newCard);
}

function updateCard({ id, config }) {
  const card = cards.value.find((c) => c.id === id);
  if (card) {
    card.config = config;
  }
}

function removeCard(id) {
  cards.value = cards.value.filter((c) => c.id !== id);
}
</script>

<template>
  <div v-loading="loading" class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold">Experiment Dashboard</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-2">
          Configurable metrics visualization with sparse data support (100K
          events)
        </p>
      </div>

      <el-button type="primary" @click="addCard" :icon="'Plus'">
        Add Chart
      </el-button>
    </div>

    <el-row :gutter="20">
      <ConfigurableChartCard
        v-for="card in cards"
        :key="card.id"
        :card-id="card.id"
        :sparse-data="sparseData"
        :available-metrics="availableMetrics"
        :initial-config="card.config"
        @update:config="updateCard"
        @remove="removeCard(card.id)"
      />
    </el-row>

    <el-empty v-if="cards.length === 0" description="No charts yet">
      <el-button type="primary" @click="addCard"
        >Add Your First Chart</el-button
      >
    </el-empty>
  </div>
</template>
