<script setup>
import { ref, watch, onMounted } from "vue";
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  labels: {
    type: Array,
    required: true,
  },
  datasets: {
    type: Array,
    required: true,
  },
  height: {
    type: Number,
    default: 200,
  },
});

const chartData = ref({
  labels: props.labels,
  datasets: props.datasets,
});

const chartOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: "bottom",
    },
    title: {
      display: false,
    },
    tooltip: {
      mode: "index",
      intersect: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        precision: 0,
      },
    },
  },
  interaction: {
    mode: "nearest",
    axis: "x",
    intersect: false,
  },
});

// Watch for prop changes
watch(
  () => [props.labels, props.datasets],
  () => {
    chartData.value = {
      labels: props.labels,
      datasets: props.datasets,
    };
  },
  { deep: true },
);
</script>

<template>
  <el-card class="chart-card">
    <template #header>
      <span class="font-bold">{{ title }}</span>
    </template>
    <div :style="{ height: height + 'px' }">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </el-card>
</template>

<style scoped>
.chart-card {
  height: 100%;
}
</style>
