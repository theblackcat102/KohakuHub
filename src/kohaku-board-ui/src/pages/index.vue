<script setup>
import { ref, onMounted } from "vue";
import { fetchExperiments } from "@/utils/api";
import { useRouter } from "vue-router";

const router = useRouter();
const experiments = ref([]);
const loading = ref(true);

onMounted(async () => {
  try {
    experiments.value = await fetchExperiments();
  } catch (error) {
    console.error("Failed to fetch experiments:", error);
  } finally {
    loading.value = false;
  }
});

function viewExperiment(id) {
  router.push(`/experiments/${id}`);
}

function formatDate(timestamp) {
  if (!timestamp) return "N/A";
  return new Date(timestamp).toLocaleString();
}

function formatSteps(steps) {
  if (steps === 0 || steps === undefined) return "N/A";
  return steps.toLocaleString();
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
        Dashboard
      </h1>
      <router-link
        to="/experiments"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-md font-medium transition-colors shadow-sm"
      >
        View All Experiments
      </router-link>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500 dark:text-gray-400">Loading experiments...</div>
    </div>

    <div
      v-else-if="experiments.length === 0"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8 text-center border border-gray-200 dark:border-gray-800"
    >
      <div class="text-gray-500 dark:text-gray-400 mb-4">No boards found</div>
      <p class="text-sm text-gray-400 dark:text-gray-500">
        Start tracking your ML experiments with KohakuBoard client library.
        <br />
        Boards are automatically discovered from:
        <code class="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded"
          >./kohakuboard</code
        >
      </p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="experiment in experiments"
        :key="experiment.id"
        @click="viewExperiment(experiment.id)"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-4 cursor-pointer hover:shadow-lg transition-all border border-gray-200 dark:border-gray-800 hover:border-blue-400 dark:hover:border-blue-600"
      >
        <div class="flex items-start justify-between mb-3">
          <h3 class="font-semibold text-lg text-gray-900 dark:text-gray-100">
            {{ experiment.name }}
          </h3>
          <span
            class="px-2 py-1 text-xs rounded font-medium"
            :class="{
              'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400':
                experiment.status === 'completed',
              'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400':
                experiment.status === 'running',
              'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400':
                experiment.status === 'stopped',
            }"
          >
            {{ experiment.status }}
          </span>
        </div>

        <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
          {{ experiment.description }}
        </p>

        <div class="grid grid-cols-2 gap-2 text-sm">
          <div>
            <div class="text-gray-500 dark:text-gray-500">Board ID</div>
            <div
              class="font-mono text-xs text-gray-900 dark:text-gray-100 truncate"
              :title="experiment.id"
            >
              {{ experiment.id }}
            </div>
          </div>
          <div>
            <div class="text-gray-500 dark:text-gray-500">Status</div>
            <div class="font-medium text-gray-900 dark:text-gray-100">
              {{ experiment.status }}
            </div>
          </div>
        </div>

        <div
          class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500 dark:text-gray-500"
        >
          Created: {{ formatDate(experiment.created_at) }}
        </div>
      </div>
    </div>
  </div>
</template>
