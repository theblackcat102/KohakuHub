<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import { useAdminStore } from "@/stores/admin";
import {
  listRepositories,
  getRepositoryDetails,
  recalculateAllRepoStorage,
} from "@/utils/api";
import { formatBytes } from "@/utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";

const router = useRouter();
const adminStore = useAdminStore();
const repositories = ref([]);
const loading = ref(false);
const recalculating = ref(false);
const selectedRepo = ref(null);
const repoDialogVisible = ref(false);

// Filters
const filterRepoType = ref("");
const filterNamespace = ref("");

// Pagination
const currentPage = ref(1);
const pageSize = ref(20);

// Sorting
const sortBy = ref("id");
const sortOrder = ref("descending");

// Computed sorted repositories
const sortedRepos = computed(() => {
  if (!repositories.value || repositories.value.length === 0) return [];

  const sorted = [...repositories.value];
  sorted.sort((a, b) => {
    let aVal, bVal;

    switch (sortBy.value) {
      case "id":
        aVal = a.id;
        bVal = b.id;
        break;
      case "full_id":
        aVal = a.full_id?.toLowerCase() || "";
        bVal = b.full_id?.toLowerCase() || "";
        break;
      case "owner_username":
        aVal = a.owner_username?.toLowerCase() || "";
        bVal = b.owner_username?.toLowerCase() || "";
        break;
      case "created_at":
        aVal = new Date(a.created_at).getTime();
        bVal = new Date(b.created_at).getTime();
        break;
      default:
        aVal = a[sortBy.value];
        bVal = b[sortBy.value];
    }

    if (sortOrder.value === "ascending") {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
    } else {
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
    }
  });

  return sorted;
});

function checkAuth() {
  if (!adminStore.token) {
    router.push("/login");
    return false;
  }
  return true;
}

async function loadRepositories() {
  if (!checkAuth()) return;

  loading.value = true;
  try {
    const response = await listRepositories(adminStore.token, {
      repo_type: filterRepoType.value || undefined,
      namespace: filterNamespace.value || undefined,
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
    });
    repositories.value = response.repositories;
  } catch (error) {
    console.error("Failed to load repositories:", error);
    if (error.response?.status === 401 || error.response?.status === 403) {
      ElMessage.error("Invalid admin token. Please login again.");
      adminStore.logout();
      router.push("/login");
    } else {
      ElMessage.error(
        error.response?.data?.detail?.error || "Failed to load repositories",
      );
    }
  } finally {
    loading.value = false;
  }
}

async function handleViewRepo(row) {
  if (!checkAuth()) return;

  try {
    selectedRepo.value = await getRepositoryDetails(
      adminStore.token,
      row.repo_type,
      row.namespace,
      row.name,
    );
    repoDialogVisible.value = true;
  } catch (error) {
    ElMessage.error(
      error.response?.data?.detail?.error ||
        "Failed to load repository details",
    );
  }
}

function formatDate(dateStr) {
  return dayjs(dateStr).format("YYYY-MM-DD HH:mm");
}

function handleSortChange({ prop, order }) {
  if (!prop || !order) {
    sortBy.value = "id";
    sortOrder.value = "descending";
    return;
  }
  sortBy.value = prop;
  sortOrder.value = order;
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

function applyFilters() {
  currentPage.value = 1;
  loadRepositories();
}

function resetFilters() {
  filterRepoType.value = "";
  filterNamespace.value = "";
  currentPage.value = 1;
  loadRepositories();
}

async function handleRecalculateAll() {
  if (!checkAuth()) return;

  try {
    await ElMessageBox.confirm(
      `This will recalculate storage for ${repositories.value.length || "all"} repositories. This may take some time. Continue?`,
      "Recalculate All Repository Storage",
      {
        type: "warning",
        confirmButtonText: "Recalculate",
        cancelButtonText: "Cancel",
      },
    );

    recalculating.value = true;
    ElMessage.info("Recalculating storage for all repositories...");

    const result = await recalculateAllRepoStorage(adminStore.token, {
      repo_type: filterRepoType.value || undefined,
      namespace: filterNamespace.value || undefined,
    });

    ElMessage.success(
      `Storage recalculated: ${result.success_count}/${result.total} succeeded${result.failure_count > 0 ? `, ${result.failure_count} failed` : ""}`,
    );

    // Reload repositories to show updated storage
    await loadRepositories();
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to recalculate storage:", err);
      ElMessage.error(
        err.response?.data?.detail?.error ||
          "Failed to recalculate repository storage",
      );
    }
  } finally {
    recalculating.value = false;
  }
}

function getProgressColor(percentage) {
  if (percentage >= 90) return "danger";
  if (percentage >= 75) return "warning";
  return "success";
}

onMounted(() => {
  loadRepositories();
});
</script>

<template>
  <AdminLayout>
    <div class="page-container">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Repository Management
        </h1>
        <el-button
          type="warning"
          @click="handleRecalculateAll"
          :loading="recalculating"
        >
          <span class="mr-2">🔄</span>
          Recalculate All Storage
        </el-button>
      </div>

      <!-- Filters -->
      <el-card class="mb-4">
        <div class="flex gap-4 items-end">
          <el-form-item label="Repository Type" class="mb-0">
            <el-select
              v-model="filterRepoType"
              placeholder="All Types"
              clearable
              style="width: 150px"
            >
              <el-option label="Model" value="model" />
              <el-option label="Dataset" value="dataset" />
              <el-option label="Space" value="space" />
            </el-select>
          </el-form-item>

          <el-form-item label="Namespace" class="mb-0">
            <el-input
              v-model="filterNamespace"
              placeholder="Filter by namespace"
              clearable
              style="width: 200px"
            />
          </el-form-item>

          <el-button type="primary" @click="applyFilters"
            >Apply Filters</el-button
          >
          <el-button @click="resetFilters">Reset</el-button>
        </div>
      </el-card>

      <!-- Repositories Table -->
      <el-card>
        <el-empty
          v-if="!loading && repositories.length === 0"
          description="No repositories found"
        />
        <el-table
          v-else
          :data="sortedRepos"
          v-loading="loading"
          stripe
          @sort-change="handleSortChange"
          :default-sort="{ prop: 'id', order: 'descending' }"
        >
          <el-table-column prop="id" label="ID" width="80" sortable="custom" />
          <el-table-column label="Type" width="100">
            <template #default="{ row }">
              <el-tag :type="getRepoTypeColor(row.repo_type)" size="small">
                {{ row.repo_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="full_id"
            label="Repository"
            min-width="250"
            sortable="custom"
          >
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <span class="font-mono">{{ row.full_id }}</span>
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
          <el-table-column
            prop="owner_username"
            label="Owner"
            width="150"
            sortable="custom"
          />
          <el-table-column
            label="Storage Used"
            width="140"
            sortable="custom"
            prop="used_bytes"
          >
            <template #default="{ row }">
              <span class="font-mono">{{ formatBytes(row.used_bytes) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Quota" width="120">
            <template #default="{ row }">
              <span v-if="row.quota_bytes" class="font-mono text-sm">
                {{ formatBytes(row.quota_bytes) }}
              </span>
              <span v-else class="text-gray-400 text-sm">Inherit</span>
            </template>
          </el-table-column>
          <el-table-column label="% Used" width="140">
            <template #default="{ row }">
              <div
                v-if="
                  row.percentage_used !== null &&
                  row.percentage_used !== undefined
                "
              >
                <el-progress
                  :percentage="Math.min(100, row.percentage_used)"
                  :status="getProgressColor(row.percentage_used)"
                  :format="(p) => `${p.toFixed(1)}%`"
                />
              </div>
              <span v-else class="text-gray-400">-</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="Created"
            width="160"
            sortable="custom"
          >
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="120" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="handleViewRepo(row)">
                View Details
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="mt-4 flex justify-center">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            layout="sizes, prev, pager, next"
            :total="repositories.length"
            @current-change="loadRepositories"
            @size-change="loadRepositories"
          />
        </div>
      </el-card>

      <!-- Repository Details Dialog -->
      <el-dialog
        v-model="repoDialogVisible"
        title="Repository Details"
        width="800px"
      >
        <div v-if="selectedRepo" class="repo-details">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{
              selectedRepo.id
            }}</el-descriptions-item>
            <el-descriptions-item label="Type">
              <el-tag :type="getRepoTypeColor(selectedRepo.repo_type)">
                {{ selectedRepo.repo_type }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Full ID" :span="2">
              <code class="font-mono">{{ selectedRepo.full_id }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="Namespace">{{
              selectedRepo.namespace
            }}</el-descriptions-item>
            <el-descriptions-item label="Name">{{
              selectedRepo.name
            }}</el-descriptions-item>
            <el-descriptions-item label="Owner">{{
              selectedRepo.owner_username
            }}</el-descriptions-item>
            <el-descriptions-item label="Visibility">
              <el-tag :type="selectedRepo.private ? 'warning' : 'success'">
                {{ selectedRepo.private ? "Private" : "Public" }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Created">{{
              formatDate(selectedRepo.created_at)
            }}</el-descriptions-item>
            <el-descriptions-item label="Files">
              <strong>{{ selectedRepo.file_count }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="Commits">
              <strong>{{ selectedRepo.commit_count }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="Total Size">
              <strong>{{ formatBytes(selectedRepo.total_size) }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="Storage Used (Tracked)">
              <strong>{{ formatBytes(selectedRepo.used_bytes) }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="Repository Quota">
              <span v-if="selectedRepo.quota_bytes">
                <strong>{{ formatBytes(selectedRepo.quota_bytes) }}</strong>
              </span>
              <span v-else class="text-gray-400">Inherit from namespace</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <template #footer>
          <el-button @click="repoDialogVisible = false">Close</el-button>
          <el-button
            type="primary"
            @click="
              $router.push(
                `/${selectedRepo.repo_type}s/${selectedRepo.namespace}/${selectedRepo.name}`,
              )
            "
          >
            View in Main App
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AdminLayout>
</template>

<style scoped>
.repo-details {
  padding: 12px 0;
}
</style>
