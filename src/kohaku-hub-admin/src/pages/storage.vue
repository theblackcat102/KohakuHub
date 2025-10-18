<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import { useAdminStore } from "@/stores/admin";
import { listS3Buckets, listS3Objects } from "@/utils/api";
import { formatBytes } from "@/utils/api";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";

const router = useRouter();
const adminStore = useAdminStore();
const buckets = ref([]);
const objects = ref([]);
const loadingBuckets = ref(false);
const loadingObjects = ref(false);
const selectedBucket = ref(null);
const currentPath = ref("");
const pathParts = ref([]);

// Computed: Parse objects into folders and files
const folderStructure = computed(() => {
  if (!objects.value || objects.value.length === 0) {
    return { folders: [], files: [] };
  }

  const folders = new Set();
  const files = [];
  const prefix = currentPath.value;

  objects.value.forEach((obj) => {
    const key = obj.key;

    // Skip if doesn't start with current path
    if (prefix && !key.startsWith(prefix)) return;

    // Get relative path from current prefix
    const relativePath = prefix ? key.substring(prefix.length) : key;

    // Check if this is a folder or file in current directory
    const slashIndex = relativePath.indexOf("/");

    if (slashIndex === -1) {
      // It's a file in current directory
      files.push({ ...obj, name: relativePath });
    } else {
      // It's inside a subfolder
      const folderName = relativePath.substring(0, slashIndex);
      folders.add(folderName);
    }
  });

  return {
    folders: Array.from(folders).sort(),
    files: files.sort((a, b) => a.name.localeCompare(b.name)),
  };
});

function checkAuth() {
  if (!adminStore.token) {
    router.push("/login");
    return false;
  }
  return true;
}

async function loadBuckets() {
  if (!checkAuth()) return;

  loadingBuckets.value = true;
  try {
    const response = await listS3Buckets(adminStore.token);
    buckets.value = response.buckets;
  } catch (error) {
    console.error("Failed to load buckets:", error);
    if (error.response?.status === 401 || error.response?.status === 403) {
      ElMessage.error("Invalid admin token. Please login again.");
      adminStore.logout();
      router.push("/login");
    } else {
      ElMessage.error(
        error.response?.data?.detail?.error || "Failed to load S3 buckets",
      );
    }
  } finally {
    loadingBuckets.value = false;
  }
}

async function loadObjects(bucket, prefix = "") {
  if (!checkAuth()) return;

  loadingObjects.value = true;
  selectedBucket.value = bucket;
  currentPath.value = prefix;

  // Update breadcrumb path parts
  if (prefix) {
    pathParts.value = prefix.split("/").filter((p) => p);
  } else {
    pathParts.value = [];
  }

  try {
    const response = await listS3Objects(adminStore.token, bucket.name, {
      prefix,
      limit: 1000,
    });
    objects.value = response.objects;
  } catch (error) {
    console.error("Failed to load objects:", error);
    ElMessage.error(
      error.response?.data?.detail?.error || "Failed to load S3 objects",
    );
  } finally {
    loadingObjects.value = false;
  }
}

function navigateToFolder(folderName) {
  const newPath = currentPath.value + folderName + "/";
  loadObjects(selectedBucket.value, newPath);
}

function navigateToBreadcrumb(index) {
  if (index === -1) {
    // Navigate to bucket root
    loadObjects(selectedBucket.value, "");
  } else {
    // Navigate to specific path level
    const newPath = pathParts.value.slice(0, index + 1).join("/") + "/";
    loadObjects(selectedBucket.value, newPath);
  }
}

function navigateUp() {
  if (pathParts.value.length === 0) {
    // Already at root, go back to buckets
    clearObjectView();
  } else {
    // Go up one level
    navigateToBreadcrumb(pathParts.value.length - 2);
  }
}

function formatDate(dateStr) {
  return dayjs(dateStr).format("YYYY-MM-DD HH:mm:ss");
}

function getBucketProgress(bucket) {
  // Return percentage for visual display
  if (!bucket.total_size) return 0;
  // Max 100GB for visual purposes
  const maxSize = 100 * 1000 * 1000 * 1000;
  return Math.min((bucket.total_size / maxSize) * 100, 100);
}

function getBucketColor(bucket) {
  const progress = getBucketProgress(bucket);
  if (progress > 80) return "danger";
  if (progress > 50) return "warning";
  return "success";
}

function handleBrowseBucket(bucket) {
  loadObjects(bucket, "");
}

function clearObjectView() {
  selectedBucket.value = null;
  objects.value = [];
  currentPath.value = "";
  pathParts.value = [];
}

function getFileIcon(fileName) {
  const ext = fileName.split(".").pop().toLowerCase();
  const iconMap = {
    // Archives
    zip: "i-carbon-archive",
    tar: "i-carbon-archive",
    gz: "i-carbon-archive",
    // Images
    jpg: "i-carbon-image",
    jpeg: "i-carbon-image",
    png: "i-carbon-image",
    gif: "i-carbon-image",
    // Documents
    pdf: "i-carbon-document-pdf",
    txt: "i-carbon-document",
    md: "i-carbon-document",
    // Code
    py: "i-carbon-logo-python",
    js: "i-carbon-code",
    json: "i-carbon-code",
    // Default
    default: "i-carbon-document",
  };
  return iconMap[ext] || iconMap.default;
}

onMounted(() => {
  loadBuckets();
});
</script>

<template>
  <AdminLayout>
    <div class="page-container">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
          S3 Storage Browser
        </h1>
        <el-button @click="loadBuckets" :icon="'Refresh'">Refresh</el-button>
      </div>

      <!-- Buckets Overview -->
      <el-card class="mb-4">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">S3 Buckets</span>
            <span class="text-sm text-gray-500">
              {{ buckets.length }} bucket(s)
            </span>
          </div>
        </template>

        <el-empty
          v-if="!loadingBuckets && buckets.length === 0"
          description="No buckets found"
        />

        <div
          v-else
          v-loading="loadingBuckets"
          class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          <div
            v-for="bucket in buckets"
            :key="bucket.name"
            class="bucket-card p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-md transition-shadow cursor-pointer"
            @click="handleBrowseBucket(bucket)"
          >
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center gap-2">
                <div class="i-carbon-data-base text-2xl text-blue-500" />
                <div>
                  <h3 class="font-bold text-gray-900 dark:text-gray-100">
                    {{ bucket.name }}
                  </h3>
                  <p class="text-xs text-gray-500">
                    {{ formatDate(bucket.creation_date) }}
                  </p>
                </div>
              </div>
            </div>

            <div class="mt-3">
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-600 dark:text-gray-400">Size:</span>
                <span class="font-semibold">{{
                  formatBytes(bucket.total_size)
                }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">Objects:</span>
                <span class="font-semibold">{{
                  bucket.object_count.toLocaleString()
                }}</span>
              </div>
            </div>

            <el-progress
              :percentage="getBucketProgress(bucket)"
              :color="getBucketColor(bucket)"
              :stroke-width="6"
              class="mt-3"
            />

            <div v-if="bucket.error" class="mt-2 text-xs text-red-500">
              Error: {{ bucket.error }}
            </div>
          </div>
        </div>
      </el-card>

      <!-- File Explorer -->
      <el-card v-if="selectedBucket">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <el-button size="small" @click="clearObjectView" :icon="'Back'">
                Back to Buckets
              </el-button>
              <span class="font-bold">{{ selectedBucket.name }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm text-gray-500">
              <span>{{ folderStructure.folders.length }} folders</span>
              <span>{{ folderStructure.files.length }} files</span>
              <span>{{ objects.length }} total objects</span>
            </div>
          </div>
        </template>

        <!-- Breadcrumb Navigation -->
        <div class="breadcrumb-container">
          <el-button
            size="small"
            @click="navigateUp"
            :icon="'ArrowLeft'"
            class="mr-2"
            :disabled="!selectedBucket"
          >
            Up
          </el-button>

          <el-breadcrumb separator="/" class="flex-1">
            <el-breadcrumb-item @click="navigateToBreadcrumb(-1)" class="breadcrumb-item">
              <div class="i-carbon-home text-blue-600" />
              <span class="ml-1">Root</span>
            </el-breadcrumb-item>
            <el-breadcrumb-item
              v-for="(part, index) in pathParts"
              :key="index"
              @click="navigateToBreadcrumb(index)"
              class="breadcrumb-item"
            >
              <div class="i-carbon-folder text-orange-600" />
              <span class="ml-1">{{ part }}</span>
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <!-- File Explorer View -->
        <div v-loading="loadingObjects">
          <el-empty
            v-if="!loadingObjects && objects.length === 0"
            description="This bucket is empty"
          />

          <div v-else class="explorer-container">
            <!-- Folders List -->
            <div v-if="folderStructure.folders.length > 0" class="mb-4">
              <div class="section-header">
                <div class="i-carbon-folder text-orange-600" />
                <span>Folders ({{ folderStructure.folders.length }})</span>
              </div>
              <div class="folder-grid">
                <div
                  v-for="folder in folderStructure.folders"
                  :key="folder"
                  class="folder-item"
                  @click="navigateToFolder(folder)"
                >
                  <div class="i-carbon-folder text-4xl text-orange-500" />
                  <span class="folder-name">{{ folder }}</span>
                </div>
              </div>
            </div>

            <!-- Files Table -->
            <div v-if="folderStructure.files.length > 0">
              <div class="section-header">
                <div class="i-carbon-document text-blue-600" />
                <span>Files ({{ folderStructure.files.length }})</span>
              </div>
              <el-table
                :data="folderStructure.files"
                stripe
                max-height="500"
              >
                <el-table-column label="Name" min-width="300">
                  <template #default="{ row }">
                    <div class="flex items-center gap-2">
                      <div :class="getFileIcon(row.name)" class="text-lg text-gray-600 dark:text-gray-400" />
                      <code class="text-sm font-mono">{{ row.name }}</code>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="Size" width="120" align="right">
                  <template #default="{ row }">
                    <span class="font-mono text-sm">{{ formatBytes(row.size) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="Storage Class" width="150">
                  <template #default="{ row }">
                    <el-tag size="small" type="info">
                      {{ row.storage_class }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Last Modified" width="180">
                  <template #default="{ row }">
                    {{ formatDate(row.last_modified) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- Empty folder message -->
            <el-empty
              v-if="folderStructure.folders.length === 0 && folderStructure.files.length === 0"
              description="This folder is empty"
            />
          </div>
        </div>
      </el-card>
    </div>
  </AdminLayout>
</template>

<style scoped>
.page-container {
  padding: 24px;
}

.bucket-card {
  background-color: var(--bg-card);
  transition: all 0.3s ease;
  border: 2px solid var(--border-default);
}

.bucket-card:hover {
  border-color: var(--color-info);
  box-shadow: var(--shadow-md);
  transform: translateY(-4px);
  background: linear-gradient(135deg, var(--bg-hover) 0%, var(--bg-card) 100%);
}

.bucket-card h3 {
  color: var(--text-primary);
}

.bucket-card .text-xs {
  color: var(--text-secondary);
}

.bucket-card .text-sm {
  color: var(--text-secondary);
}

.bucket-card .font-semibold {
  color: var(--text-primary);
}

/* File Explorer Styles */
.breadcrumb-container {
  display: flex;
  align-items: center;
  padding: 16px;
  background-color: var(--bg-hover);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid var(--border-default);
}

.breadcrumb-item {
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
}

.breadcrumb-item:hover {
  color: var(--color-info);
  transform: scale(1.05);
}

.breadcrumb-item span {
  font-weight: 500;
  color: var(--text-primary);
}

.explorer-container {
  margin-top: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: var(--bg-hover);
  border-radius: 8px;
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--text-primary);
  border-left: 4px solid var(--color-info);
}

.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.folder-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background-color: var(--bg-card);
  border: 2px solid var(--border-default);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  gap: 12px;
}

.folder-item:hover {
  border-color: var(--color-warning);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, var(--bg-card) 100%);
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.folder-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  text-align: center;
  word-break: break-word;
  max-width: 100%;
}

/* Table styling */
:deep(.el-table) {
  background-color: var(--bg-card);
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th) {
  background-color: var(--bg-hover);
  color: var(--text-primary);
  font-weight: 600;
}

:deep(.el-table td) {
  color: var(--text-primary);
}

:deep(.el-table__body tr:hover > td) {
  background-color: var(--bg-hover) !important;
}

/* Breadcrumb styling */
:deep(.el-breadcrumb__inner) {
  display: flex;
  align-items: center;
  font-weight: 500;
  color: var(--text-primary);
}

:deep(.el-breadcrumb__inner:hover) {
  color: var(--color-info);
}
</style>
