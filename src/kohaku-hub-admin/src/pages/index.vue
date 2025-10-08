<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import { useAdminStore } from "@/stores/admin";
import { getDetailedStats, getTopRepositories } from "@/utils/api";
import { formatBytes } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();
const stats = ref(null);
const topRepos = ref([]);
const loading = ref(false);

async function loadStats() {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  loading.value = true;
  try {
    stats.value = await getDetailedStats(adminStore.token);
    const topReposData = await getTopRepositories(adminStore.token, 5, "commits");
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
        <!-- Users Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-blue-500 to-blue-600">
            <div class="i-carbon-user-multiple text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">{{ stats?.users?.total || 0 }}</div>
            <div class="text-lg opacity-90 mb-2">Total Users</div>
            <div class="text-sm opacity-75">
              Active: {{ stats?.users?.active || 0 }} |
              Verified: {{ stats?.users?.verified || 0 }}
            </div>
          </div>
        </el-card>

        <!-- Organizations Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-purple-500 to-purple-600">
            <div class="i-carbon-enterprise text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.organizations?.total || 0 }}
            </div>
            <div class="text-lg opacity-90">Organizations</div>
          </div>
        </el-card>

        <!-- Total Repositories Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-green-500 to-green-600">
            <div class="i-carbon-data-base text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.repositories?.total || 0 }}
            </div>
            <div class="text-lg opacity-90 mb-2">Total Repositories</div>
            <div class="text-sm opacity-75">
              Models: {{ stats?.repositories?.by_type?.model || 0 }} |
              Datasets: {{ stats?.repositories?.by_type?.dataset || 0 }}
            </div>
          </div>
        </el-card>

        <!-- Commits Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-orange-500 to-orange-600">
            <div class="i-carbon-git-commit text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.commits?.total || 0 }}
            </div>
            <div class="text-lg opacity-90">Total Commits</div>
          </div>
        </el-card>

        <!-- Storage Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-cyan-500 to-cyan-600">
            <div class="i-carbon-data-volume text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ formatBytes(stats?.storage?.total_used || 0) }}
            </div>
            <div class="text-lg opacity-90 mb-2">Total Storage</div>
            <div class="text-sm opacity-75">
              Private: {{ formatBytes(stats?.storage?.private_used || 0) }} |
              Public: {{ formatBytes(stats?.storage?.public_used || 0) }}
            </div>
          </div>
        </el-card>

        <!-- LFS Objects Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-pink-500 to-pink-600">
            <div class="i-carbon-document text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.lfs?.total_objects || 0 }}
            </div>
            <div class="text-lg opacity-90 mb-2">LFS Objects</div>
            <div class="text-sm opacity-75">
              {{ formatBytes(stats?.lfs?.total_size || 0) }}
            </div>
          </div>
        </el-card>
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
                <el-tag v-if="row.private" type="warning" size="small" effect="plain">
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
          <el-button
            @click="$router.push('/commits')"
            :icon="'GitCommit'"
          >
            View Commits
          </el-button>
          <el-button
            @click="$router.push('/storage')"
            :icon="'Storage'"
          >
            Browse Storage
          </el-button>
          <el-button
            @click="$router.push('/quotas')"
            :icon="'DataVolume'"
          >
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
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card-wrapper {
  transition: transform 0.2s;
}

.stat-card-wrapper:hover {
  transform: translateY(-4px);
}

.stat-card {
  text-align: center;
  padding: 32px;
  border-radius: 8px;
  color: white;
  background: linear-gradient(
    135deg,
    var(--tw-gradient-from),
    var(--tw-gradient-to)
  );
}

.from-blue-500 {
  --tw-gradient-from: #3b82f6;
}
.to-blue-600 {
  --tw-gradient-to: #2563eb;
}

.from-purple-500 {
  --tw-gradient-from: #a855f7;
}
.to-purple-600 {
  --tw-gradient-to: #9333ea;
}

.from-green-500 {
  --tw-gradient-from: #22c55e;
}
.to-green-600 {
  --tw-gradient-to: #16a34a;
}

.from-orange-500 {
  --tw-gradient-from: #f97316;
}
.to-orange-600 {
  --tw-gradient-to: #ea580c;
}

.from-cyan-500 {
  --tw-gradient-from: #06b6d4;
}
.to-cyan-600 {
  --tw-gradient-to: #0891b2;
}

.from-pink-500 {
  --tw-gradient-from: #ec4899;
}
.to-pink-600 {
  --tw-gradient-to: #db2777;
}
</style>
