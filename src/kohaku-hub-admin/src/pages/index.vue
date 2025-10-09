<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import StatsCard from "@/components/StatsCard.vue";
import { useAdminStore } from "@/stores/admin";
import { getDetailedStats, getTopRepositories } from "@/utils/api";
import { formatBytes } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();
const stats = ref(null);
const topRepos = ref([]);
const loading = ref(false);

const hasData = computed(() => stats.value !== null);

async function loadStats() {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  loading.value = true;
  try {
    stats.value = await getDetailedStats(adminStore.token);
    const topReposData = await getTopRepositories(
      adminStore.token,
      5,
      "commits",
    );
    topRepos.value = topReposData.top_repositories;
  } catch (error) {
    console.error("Failed to load stats:", error);
    if (error.response?.status === 401 || error.response?.status === 403) {
      ElMessage.error("Invalid admin token. Please login again.");
      adminStore.logout();
      router.push("/login");
    } else {
      ElMessage.error(
        error.response?.data?.detail?.error || "Failed to load system stats",
      );
    }
  } finally {
    loading.value = false;
  }
}

function getRepoTypeColor(type) {
  switch (type) {
    case "model":
      return "primary";
    case "dataset":
      return "success";
    case "space":
      return "warning";
    default:
      return "info";
  }
}

onMounted(() => {
  loadStats();
});
</script>

<template>
  <AdminLayout>
    <div class="page-container">
      <h1 class="text-3xl font-bold mb-6 text-gray-900 dark:text-gray-100">
        Dashboard
      </h1>

      <div v-loading="loading" class="stats-grid">
        <StatsCard
          title="Total Users"
          :value="stats?.users?.total || 0"
          :subtitle="`Active: ${stats?.users?.active || 0} | Verified: ${stats?.users?.verified || 0}`"
          icon="i-carbon-user-multiple"
          color="blue"
        />

        <StatsCard
          title="Organizations"
          :value="stats?.organizations?.total || 0"
          icon="i-carbon-enterprise"
          color="purple"
        />

        <StatsCard
          title="Total Repositories"
          :value="stats?.repositories?.total || 0"
          :subtitle="`Models: ${stats?.repositories?.by_type?.model || 0} | Datasets: ${stats?.repositories?.by_type?.dataset || 0}`"
          icon="i-carbon-data-base"
          color="green"
        />

        <StatsCard
          title="Total Commits"
          :value="stats?.commits?.total || 0"
          icon="i-carbon-version"
          color="orange"
        />

        <StatsCard
          title="Total Storage"
          :value="formatBytes(stats?.storage?.total_used || 0)"
          :subtitle="`Private: ${formatBytes(stats?.storage?.private_used || 0)} | Public: ${formatBytes(stats?.storage?.public_used || 0)}`"
          icon="i-carbon-data-volume"
          color="cyan"
        />

        <StatsCard
          title="LFS Objects"
          :value="stats?.lfs?.total_objects || 0"
          :subtitle="formatBytes(stats?.lfs?.total_size || 0)"
          icon="i-carbon-document"
          color="pink"
        />
      </div>

      <!-- Top Contributors -->
      <el-card class="mb-6" v-if="stats?.commits?.top_contributors?.length > 0">
        <template #header>
          <span class="font-bold">Top Contributors</span>
        </template>
        <el-table :data="stats.commits.top_contributors" stripe>
          <el-table-column prop="username" label="Username" />
          <el-table-column label="Commits" width="120" align="right">
            <template #default="{ row }">
              <el-tag type="success">{{ row.commit_count }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Top Repositories by Commits -->
      <el-card class="mb-6" v-if="topRepos.length > 0">
        <template #header>
          <span class="font-bold">Top Repositories by Commits</span>
        </template>
        <el-table :data="topRepos" stripe>
          <el-table-column label="Repository" min-width="250">
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <el-tag :type="getRepoTypeColor(row.repo_type)" size="small">
                  {{ row.repo_type }}
                </el-tag>
                <span class="font-mono">{{ row.repo_full_id }}</span>
                <el-tag
                  v-if="row.private"
                  type="warning"
                  size="small"
                  effect="plain"
                >
                  Private
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Commits" width="120" align="right">
            <template #default="{ row }">
              <el-tag type="success">{{ row.commit_count }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Quick Actions -->
      <div class="mt-8">
        <h2 class="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
          Quick Actions
        </h2>
        <div class="flex gap-4 flex-wrap">
          <el-button
            type="primary"
            @click="$router.push('/users')"
            :icon="'User'"
          >
            Manage Users
          </el-button>
          <el-button
            type="success"
            @click="$router.push('/repositories')"
            :icon="'DataBase'"
          >
            View Repositories
          </el-button>
          <el-button @click="$router.push('/commits')" :icon="'GitCommit'">
            View Commits
          </el-button>
          <el-button @click="$router.push('/storage')" :icon="'Storage'">
            Browse Storage
          </el-button>
          <el-button @click="$router.push('/quotas')" :icon="'DataVolume'">
            Manage Quotas
          </el-button>
          <el-button @click="loadStats" :icon="'Renew'">
            Refresh Stats
          </el-button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.page-container {
  padding: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}
</style>
