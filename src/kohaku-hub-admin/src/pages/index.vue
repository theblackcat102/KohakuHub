<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import { useAdminStore } from "@/stores/admin";
import { getSystemStats } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();
const stats = ref(null);
const loading = ref(false);

async function loadStats() {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  loading.value = true;
  try {
    stats.value = await getSystemStats(adminStore.token);
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
            <div class="text-5xl font-bold mb-2">{{ stats?.users || 0 }}</div>
            <div class="text-lg opacity-90">Total Users</div>
          </div>
        </el-card>

        <!-- Organizations Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-purple-500 to-purple-600">
            <div class="i-carbon-enterprise text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.organizations || 0 }}
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
            <div class="text-lg opacity-90">Total Repositories</div>
          </div>
        </el-card>

        <!-- Private Repositories Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-orange-500 to-orange-600">
            <div class="i-carbon-locked text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.repositories?.private || 0 }}
            </div>
            <div class="text-lg opacity-90">Private Repos</div>
          </div>
        </el-card>

        <!-- Public Repositories Card -->
        <el-card shadow="hover" class="stat-card-wrapper">
          <div class="stat-card from-cyan-500 to-cyan-600">
            <div class="i-carbon-unlocked text-5xl mb-3 opacity-80" />
            <div class="text-5xl font-bold mb-2">
              {{ stats?.repositories?.public || 0 }}
            </div>
            <div class="text-lg opacity-90">Public Repos</div>
          </div>
        </el-card>
      </div>

      <!-- Quick Actions -->
      <div class="mt-8">
        <h2 class="text-2xl font-bold mb-4 text-gray-900 dark:text-gray-100">
          Quick Actions
        </h2>
        <div class="flex gap-4">
          <el-button
            type="primary"
            @click="$router.push('/users')"
            :icon="'User'"
          >
            Manage Users
          </el-button>
          <el-button
            type="success"
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
</style>
