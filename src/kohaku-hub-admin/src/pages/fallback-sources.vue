<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import { useAdminStore } from "@/stores/admin";
import {
  listFallbackSources,
  createFallbackSource,
  updateFallbackSource,
  deleteFallbackSource,
  getFallbackCacheStats,
  clearFallbackCache,
} from "@/utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";

const router = useRouter();
const adminStore = useAdminStore();

const sources = ref([]);
const cacheStats = ref(null);
const loading = ref(false);

// Form dialog
const dialogVisible = ref(false);
const dialogMode = ref("create"); // 'create' or 'edit'
const formData = ref({
  id: null,
  namespace: "",
  url: "",
  token: "",
  priority: 100,
  name: "",
  source_type: "huggingface",
  enabled: true,
});

function checkAuth() {
  if (!adminStore.token) {
    router.push("/login");
    return false;
  }
  return true;
}

async function loadSources() {
  if (!checkAuth()) return;

  loading.value = true;
  try {
    sources.value = await listFallbackSources(adminStore.token);
  } catch (error) {
    console.error("Failed to load fallback sources:", error);
    ElMessage.error(
      error.response?.data?.detail?.error || "Failed to load fallback sources",
    );
  } finally {
    loading.value = false;
  }
}

async function loadCacheStats() {
  if (!checkAuth()) return;

  try {
    cacheStats.value = await getFallbackCacheStats(adminStore.token);
  } catch (error) {
    console.error("Failed to load cache stats:", error);
  }
}

function openCreateDialog() {
  dialogMode.value = "create";
  formData.value = {
    id: null,
    namespace: "",
    url: "",
    token: "",
    priority: 100,
    name: "",
    source_type: "huggingface",
    enabled: true,
  };
  dialogVisible.value = true;
}

function openEditDialog(source) {
  dialogMode.value = "edit";
  formData.value = {
    id: source.id,
    namespace: source.namespace,
    url: source.url,
    token: source.token || "",
    priority: source.priority,
    name: source.name,
    source_type: source.source_type,
    enabled: source.enabled,
  };
  dialogVisible.value = true;
}

async function handleSubmit() {
  if (!checkAuth()) return;

  loading.value = true;
  try {
    if (dialogMode.value === "create") {
      await createFallbackSource(adminStore.token, formData.value);
      ElMessage.success("Fallback source created successfully");
    } else {
      const { id, ...updateData } = formData.value;
      await updateFallbackSource(adminStore.token, id, updateData);
      ElMessage.success("Fallback source updated successfully");
    }

    dialogVisible.value = false;
    await loadSources();
    await loadCacheStats();
  } catch (error) {
    console.error("Failed to save fallback source:", error);
    ElMessage.error(
      error.response?.data?.detail?.error || "Failed to save fallback source",
    );
  } finally {
    loading.value = false;
  }
}

async function handleDelete(source) {
  if (!checkAuth()) return;

  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete "${source.name}"? This action cannot be undone.`,
      "Confirm Delete",
      {
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        type: "warning",
      },
    );

    loading.value = true;
    await deleteFallbackSource(adminStore.token, source.id);
    ElMessage.success(`Fallback source "${source.name}" deleted`);
    await loadSources();
    await loadCacheStats();
  } catch (error) {
    if (error !== "cancel") {
      console.error("Failed to delete fallback source:", error);
      ElMessage.error(
        error.response?.data?.detail?.error ||
          "Failed to delete fallback source",
      );
    }
  } finally {
    loading.value = false;
  }
}

async function handleToggleEnabled(source) {
  if (!checkAuth()) return;

  loading.value = true;
  try {
    await updateFallbackSource(adminStore.token, source.id, {
      enabled: !source.enabled,
    });
    ElMessage.success(
      `Source "${source.name}" ${!source.enabled ? "enabled" : "disabled"}`,
    );
    await loadSources();
  } catch (error) {
    console.error("Failed to toggle source:", error);
    ElMessage.error(
      error.response?.data?.detail?.error || "Failed to toggle source",
    );
  } finally {
    loading.value = false;
  }
}

async function handleClearCache() {
  if (!checkAuth()) return;

  try {
    await ElMessageBox.confirm(
      "Are you sure you want to clear the fallback cache? This will remove all cached repository→source mappings.",
      "Confirm Clear Cache",
      {
        confirmButtonText: "Clear Cache",
        cancelButtonText: "Cancel",
        type: "warning",
      },
    );

    loading.value = true;
    const result = await clearFallbackCache(adminStore.token);
    ElMessage.success(result.message);
    await loadCacheStats();
  } catch (error) {
    if (error !== "cancel") {
      console.error("Failed to clear cache:", error);
      ElMessage.error(
        error.response?.data?.detail?.error || "Failed to clear cache",
      );
    }
  } finally {
    loading.value = false;
  }
}

function formatDate(dateStr) {
  return dayjs(dateStr).format("YYYY-MM-DD HH:mm:ss");
}

onMounted(() => {
  loadSources();
  loadCacheStats();
});
</script>

<template>
  <AdminLayout>
    <div class="fallback-sources-page">
      <div class="page-header">
        <h1>Fallback Sources</h1>
        <p>
          Manage external repository sources (HuggingFace, other KohakuHub
          instances)
        </p>
      </div>

      <!-- Cache Stats Card -->
      <el-card v-if="cacheStats" class="stats-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>Cache Statistics</span>
            <el-button
              type="danger"
              size="small"
              @click="handleClearCache"
              :loading="loading"
            >
              <i class="i-carbon-trash-can mr-1"></i>
              Clear Cache
            </el-button>
          </div>
        </template>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">Size</div>
            <div class="stat-value">{{ cacheStats.size }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Max Size</div>
            <div class="stat-value">{{ cacheStats.maxsize }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">TTL</div>
            <div class="stat-value">{{ cacheStats.ttl_seconds }}s</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Usage</div>
            <div class="stat-value">{{ cacheStats.usage_percent }}%</div>
          </div>
        </div>
      </el-card>

      <!-- Sources List Card -->
      <el-card class="sources-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>Configured Sources</span>
            <el-button
              type="primary"
              size="small"
              @click="openCreateDialog"
              :loading="loading"
            >
              <i class="i-carbon-add mr-1"></i>
              Add Source
            </el-button>
          </div>
        </template>

        <div v-if="loading && sources.length === 0" class="empty-state">
          <i class="i-carbon-loading animate-spin text-4xl"></i>
          <p>Loading...</p>
        </div>

        <div v-else-if="sources.length === 0" class="empty-state">
          <i class="i-carbon-cloud-offline text-6xl opacity-30"></i>
          <p>No fallback sources configured</p>
          <p class="text-sm opacity-60">
            Add a source to enable fallback to HuggingFace or other hubs
          </p>
        </div>

        <div v-else class="sources-list">
          <div
            v-for="source in sources"
            :key="source.id"
            class="source-item"
            :class="{ disabled: !source.enabled }"
          >
            <div class="source-header">
              <div class="source-title">
                <h3>{{ source.name }}</h3>
                <div class="badges">
                  <el-tag
                    :type="
                      source.source_type === 'huggingface'
                        ? 'primary'
                        : 'success'
                    "
                    size="small"
                  >
                    {{ source.source_type }}
                  </el-tag>
                  <el-tag
                    :type="source.enabled ? 'success' : 'info'"
                    size="small"
                  >
                    {{ source.enabled ? "Enabled" : "Disabled" }}
                  </el-tag>
                  <el-tag v-if="source.namespace" type="warning" size="small">
                    {{ source.namespace }}
                  </el-tag>
                </div>
              </div>
              <div class="source-actions">
                <el-button
                  :type="source.enabled ? 'default' : 'success'"
                  size="small"
                  @click="handleToggleEnabled(source)"
                  :loading="loading"
                >
                  {{ source.enabled ? "Disable" : "Enable" }}
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  @click="openEditDialog(source)"
                  :loading="loading"
                >
                  <i class="i-carbon-edit"></i>
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="handleDelete(source)"
                  :loading="loading"
                >
                  <i class="i-carbon-trash-can"></i>
                </el-button>
              </div>
            </div>

            <div class="source-details">
              <div class="detail-row">
                <span class="detail-label">URL:</span>
                <code>{{ source.url }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">Priority:</span>
                <span>{{ source.priority }} (lower = higher priority)</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Namespace:</span>
                <span>{{ source.namespace || "(global)" }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span>{{ formatDate(source.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- Create/Edit Dialog -->
      <el-dialog
        v-model="dialogVisible"
        :title="
          dialogMode === 'create'
            ? 'Create Fallback Source'
            : 'Edit Fallback Source'
        "
        width="600px"
      >
        <el-form :model="formData" label-width="120px">
          <el-form-item label="Name" required>
            <el-input v-model="formData.name" placeholder="HuggingFace" />
          </el-form-item>

          <el-form-item label="URL" required>
            <el-input
              v-model="formData.url"
              placeholder="https://huggingface.co"
            />
          </el-form-item>

          <el-form-item label="Source Type" required>
            <el-select v-model="formData.source_type" style="width: 100%">
              <el-option label="HuggingFace" value="huggingface" />
              <el-option label="KohakuHub" value="kohakuhub" />
            </el-select>
          </el-form-item>

          <el-form-item label="Token">
            <el-input
              v-model="formData.token"
              type="password"
              placeholder="Optional API token (hf_xxx...)"
              show-password
            />
            <div class="form-help">
              Admin-configured token for accessing private repos
            </div>
          </el-form-item>

          <el-form-item label="Priority" required>
            <el-input-number
              v-model="formData.priority"
              :min="1"
              :max="1000"
              style="width: 100%"
            />
            <div class="form-help">
              Lower values = higher priority (checked first)
            </div>
          </el-form-item>

          <el-form-item label="Namespace">
            <el-input
              v-model="formData.namespace"
              placeholder="(empty for global)"
            />
            <div class="form-help">
              Empty = global, or specify user/org name
            </div>
          </el-form-item>

          <el-form-item label="Enabled">
            <el-switch v-model="formData.enabled" />
          </el-form-item>
        </el-form>

        <template #footer>
          <el-button @click="dialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            {{ dialogMode === "create" ? "Create" : "Update" }}
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AdminLayout>
</template>

<style scoped>
.fallback-sources-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--el-text-color-secondary);
  margin: 0;
}

.stats-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.sources-card {
  margin-bottom: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--el-text-color-secondary);
}

.empty-state i {
  display: block;
  margin-bottom: 16px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;
}

.source-item:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.source-item.disabled {
  opacity: 0.5;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.source-title h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.badges {
  display: flex;
  gap: 8px;
}

.source-actions {
  display: flex;
  gap: 8px;
}

.source-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  display: flex;
  align-items: center;
  font-size: 14px;
}

.detail-label {
  font-weight: 600;
  min-width: 100px;
  color: var(--el-text-color-secondary);
}

.detail-row code {
  background: var(--el-fill-color-light);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: "Consolas", "Monaco", monospace;
}

.form-help {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>
