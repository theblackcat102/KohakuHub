<script setup>
import { ref, onMounted } from "vue";
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
const objectPrefix = ref("");

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
  objectPrefix.value = prefix;

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
  loadObjects(bucket);
}

function handleFilterByPrefix() {
  if (selectedBucket.value) {
    loadObjects(selectedBucket.value, objectPrefix.value);
  }
}

function clearObjectView() {
  selectedBucket.value = null;
  objects.value = [];
  objectPrefix.value = "";
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
                <span class="font-semibold">{{ formatBytes(bucket.total_size) }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-600 dark:text-gray-400">Objects:</span>
                <span class="font-semibold">{{ bucket.object_count.toLocaleString() }}</span>
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

      <!-- Object Browser -->
      <el-card v-if="selectedBucket">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <el-button size="small" @click="clearObjectView" :icon="'Back'">
                Back to Buckets
              </el-button>
              <span class="font-bold">Bucket: {{ selectedBucket.name }}</span>
            </div>
          </div>
        </template>

        <!-- Prefix Filter -->
        <div class="mb-4 flex gap-2">
          <el-input
            v-model="objectPrefix"
            placeholder="Filter by prefix (e.g., lfs/, models/)"
            clearable
            style="max-width: 400px"
            @keyup.enter="handleFilterByPrefix"
          >
            <template #prepend>
              <div class="i-carbon-search" />
            </template>
          </el-input>
          <el-button type="primary" @click="handleFilterByPrefix">
            Filter
          </el-button>
        </div>

        <!-- Objects Table -->
        <el-empty
          v-if="!loadingObjects && objects.length === 0"
          description="No objects found in this bucket"
        />
        <el-table
          v-else
          :data="objects"
          v-loading="loadingObjects"
          stripe
          max-height="600"
        >
          <el-table-column label="Key" min-width="400">
            <template #default="{ row }">
              <code class="text-xs font-mono text-gray-700 dark:text-gray-300">{{
                row.key
              }}</code>
            </template>
          </el-table-column>
          <el-table-column label="Size" width="120" align="right">
            <template #default="{ row }">
              {{ formatBytes(row.size) }}
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

        <div class="mt-4 text-sm text-gray-500">
          Showing {{ objects.length }} object(s)
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
  background-color: white;
}

html.dark .bucket-card {
  background-color: #1a1a1a;
}

.bucket-card:hover {
  border-color: #409eff;
}
</style>
