<script setup>
import { ref, computed, onMounted } from "vue";
import { fetchExperiments } from "@/utils/api";
import { useRouter } from "vue-router";

const router = useRouter();
const experiments = ref([]);
const loading = ref(true);
const searchQuery = ref("");
const statusFilter = ref("all");

onMounted(async () => {
  try {
    experiments.value = await fetchExperiments();
  } catch (error) {
    console.error("Failed to fetch experiments:", error);
  } finally {
    loading.value = false;
  }
});

const filteredExperiments = computed(() => {
  let filtered = experiments.value;

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(
      (exp) =>
        exp.name.toLowerCase().includes(query) ||
        exp.id.toLowerCase().includes(query) ||
        (exp.description && exp.description.toLowerCase().includes(query)),
    );
  }

  // Filter by status
  if (statusFilter.value !== "all") {
    filtered = filtered.filter((exp) => exp.status === statusFilter.value);
  }

  return filtered;
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
    <h1 class="text-3xl font-bold mb-6">Experiments</h1>

    <div class="card mb-6">
      <div class="flex gap-4">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search experiments..."
          class="input flex-1"
        />
        <select v-model="statusFilter" class="input">
          <option value="all">All Status</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="stopped">Stopped</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="text-gray-500 dark:text-gray-400">Loading experiments...</div>
    </div>

    <div v-else class="card">
      <table class="w-full">
        <thead class="border-b border-gray-200 dark:border-gray-700">
          <tr>
            <th class="text-left py-3 px-4">Name</th>
            <th class="text-left py-3 px-4">Board ID</th>
            <th class="text-left py-3 px-4">Status</th>
            <th class="text-left py-3 px-4">Created</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="experiment in filteredExperiments"
            :key="experiment.id"
            @click="viewExperiment(experiment.id)"
            class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
          >
            <td class="py-3 px-4">
              <div class="font-medium">{{ experiment.name }}</div>
              <div class="text-sm text-gray-500 dark:text-gray-400">
                {{ experiment.description }}
              </div>
            </td>
            <td class="py-3 px-4 font-mono text-sm">
              {{ experiment.id }}
            </td>
            <td class="py-3 px-4">
              <span
                class="px-2 py-1 text-xs rounded"
                :class="{
                  'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200':
                    experiment.status === 'completed',
                  'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200':
                    experiment.status === 'running',
                  'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200':
                    experiment.status === 'stopped',
                }"
              >
                {{ experiment.status }}
              </span>
            </td>
            <td class="py-3 px-4 text-sm text-gray-500 dark:text-gray-400">
              {{ formatDate(experiment.created_at) }}
            </td>
          </tr>
        </tbody>
      </table>

      <div
        v-if="filteredExperiments.length === 0"
        class="text-center py-8 text-gray-500 dark:text-gray-400"
      >
        No experiments match your filters
      </div>
    </div>
  </div>
</template>
