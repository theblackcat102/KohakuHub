<!-- src/kohaku-hub-ui/src/pages/[type]s/[namespace]/[name]/upload/[branch].vue -->
<template>
  <div class="container-main">
    <!-- Breadcrumb -->
    <el-breadcrumb separator="/" class="mb-6 text-gray-700 dark:text-gray-300">
      <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s` }">
        {{ repoTypeLabel }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${namespace}` }">
        {{ namespace }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s/${namespace}/${name}` }">
        {{ name }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>Upload Files</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- Page Header -->
    <div class="card mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="i-carbon-cloud-upload text-3xl text-blue-500" />
          <div>
            <h1 class="text-2xl font-bold">Upload Files</h1>
            <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Upload files to <strong>{{ namespace }}/{{ name }}</strong> on
              branch <el-tag size="small">{{ branch }}</el-tag>
            </div>
          </div>
        </div>
        <el-button @click="goBack">
          <div class="i-carbon-arrow-left inline-block mr-1" />
          Back to Repository
        </el-button>
      </div>
    </div>

    <!-- Upload Form -->
    <div class="card">
      <h2 class="text-xl font-semibold mb-4">Select Files</h2>

      <!-- File Drop Zone -->
      <div
        class="upload-zone"
        :class="{ 'is-dragover': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div class="text-center py-12">
          <div
            class="i-carbon-cloud-upload text-6xl text-gray-400 dark:text-gray-500 mb-4 inline-block"
          />
          <div class="text-lg font-medium mb-2">
            Drop files here or click to browse
          </div>
          <div class="text-sm text-gray-500 dark:text-gray-400 mb-4">
            You can upload multiple files at once
          </div>
          <input
            ref="fileInput"
            type="file"
            multiple
            class="hidden"
            @change="handleFileSelect"
          />
          <el-button type="primary" @click="$refs.fileInput.click()">
            <div class="i-carbon-document-add inline-block mr-1" />
            Choose Files
          </el-button>
        </div>
      </div>

      <!-- File List -->
      <div v-if="files.length > 0" class="mt-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold">
            Files to Upload ({{ files.length }})
          </h3>
          <el-button size="small" @click="clearFiles">
            <div class="i-carbon-trash-can inline-block mr-1" />
            Clear All
          </el-button>
        </div>

        <div class="file-list">
          <div
            v-for="(fileItem, index) in files"
            :key="index"
            class="file-item"
          >
            <div class="flex items-center gap-3 flex-1">
              <div class="i-carbon-document text-2xl text-blue-500" />
              <div class="flex-1 min-w-0">
                <div class="font-medium truncate">{{ fileItem.file.name }}</div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {{ formatSize(fileItem.file.size) }}
                </div>
              </div>
              <div class="flex-shrink-0" style="width: 300px">
                <el-input
                  v-model="fileItem.path"
                  size="small"
                  placeholder="Path in repository"
                >
                  <template #prepend>/</template>
                </el-input>
              </div>
            </div>
            <el-button
              size="small"
              text
              @click="removeFile(index)"
              class="ml-2"
            >
              <div class="i-carbon-close text-lg" />
            </el-button>
          </div>
        </div>
      </div>

      <!-- Commit Information -->
      <div
        v-if="files.length > 0"
        class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700"
      >
        <h3 class="text-lg font-semibold mb-4">Commit Information</h3>

        <el-form :model="commitForm" label-position="top">
          <el-form-item label="Commit message" required>
            <el-input
              v-model="commitForm.message"
              placeholder="Upload files via web interface"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="Commit description (optional)">
            <el-input
              v-model="commitForm.description"
              type="textarea"
              :rows="3"
              placeholder="Additional details about this upload..."
            />
          </el-form-item>
        </el-form>

        <!-- Upload Progress -->
        <div v-if="uploading" class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium">Uploading...</span>
            <span class="text-sm text-gray-600 dark:text-gray-400">
              {{ Math.round(uploadProgress * 100) }}%
            </span>
          </div>
          <el-progress
            :percentage="Math.round(uploadProgress * 100)"
            :status="uploadProgress === 1 ? 'success' : undefined"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-3">
          <el-button
            type="primary"
            size="large"
            :disabled="!canUpload"
            :loading="uploading"
            @click="handleUpload"
          >
            <div
              v-if="!uploading"
              class="i-carbon-cloud-upload inline-block mr-1"
            />
            {{ uploading ? "Uploading..." : "Upload Files" }}
          </el-button>
          <el-button size="large" @click="goBack" :disabled="uploading">
            Cancel
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { repoAPI } from "@/utils/api";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// Route params
const repoType = computed(() => {
  const path = route.path;
  if (path.includes("/models/")) return "model";
  if (path.includes("/datasets/")) return "dataset";
  if (path.includes("/spaces/")) return "space";
  return "model";
});
const namespace = computed(() => route.params.namespace);
const name = computed(() => route.params.name);
const branch = computed(() => route.params.branch || "main");

// State
const files = ref([]);
const isDragging = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const fileInput = ref(null);

const commitForm = ref({
  message: "Upload files via web interface",
  description: "",
});

// Computed
const repoTypeLabel = computed(() => {
  const labels = { model: "Models", dataset: "Datasets", space: "Spaces" };
  return labels[repoType.value] || "Models";
});

const canUpload = computed(() => {
  return (
    files.value.length > 0 &&
    commitForm.value.message.trim() !== "" &&
    !uploading.value &&
    files.value.every((f) => f.path.trim() !== "")
  );
});

// Methods
function handleDrop(e) {
  isDragging.value = false;
  const droppedFiles = Array.from(e.dataTransfer.files);
  addFiles(droppedFiles);
}

function handleFileSelect(e) {
  const selectedFiles = Array.from(e.target.files);
  addFiles(selectedFiles);
  // Reset input so same file can be selected again
  e.target.value = "";
}

function addFiles(newFiles) {
  const fileItems = newFiles.map((file) => ({
    file,
    path: file.webkitRelativePath || file.name,
  }));
  files.value.push(...fileItems);
}

function removeFile(index) {
  files.value.splice(index, 1);
}

function clearFiles() {
  files.value = [];
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}

async function handleUpload() {
  if (!canUpload.value) return;

  uploading.value = true;
  uploadProgress.value = 0;

  try {
    await repoAPI.uploadFiles(
      repoType.value,
      namespace.value,
      name.value,
      branch.value,
      {
        files: files.value,
        message: commitForm.value.message,
        description: commitForm.value.description,
      },
      (progress) => {
        uploadProgress.value = progress;
      },
    );

    ElMessage.success("Files uploaded successfully");

    // Wait a bit to show 100% progress
    setTimeout(() => {
      router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
    }, 500);
  } catch (err) {
    const errorMsg = err.response?.data?.detail || "Failed to upload files";
    ElMessage.error(errorMsg);
    console.error("Upload error:", err);
  } finally {
    uploading.value = false;
  }
}

function goBack() {
  router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
}

// Lifecycle
onMounted(() => {
  // Check if user has permission to upload
  if (!authStore.isAuthenticated) {
    ElMessage.error("You must be logged in to upload files");
    router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
    return;
  }

  if (!authStore.canWriteToNamespace(namespace.value)) {
    ElMessage.error("You don't have permission to upload to this repository");
    router.push(`/${repoType.value}s/${namespace.value}/${name.value}`);
    return;
  }
});
</script>

<style scoped>
.upload-zone {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  background-color: #f9fafb;
  transition: all 0.3s;
  cursor: pointer;
}

.dark .upload-zone {
  border-color: #374151;
  background-color: #1f2937;
}

.upload-zone:hover {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.dark .upload-zone:hover {
  border-color: #60a5fa;
  background-color: #1e3a5f;
}

.upload-zone.is-dragover {
  border-color: #3b82f6;
  background-color: #dbeafe;
}

.dark .upload-zone.is-dragover {
  border-color: #60a5fa;
  background-color: #1e40af;
}

.file-list {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.dark .file-list {
  border-color: #374151;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background-color: white;
  transition: background-color 0.2s;
}

.dark .file-item {
  border-bottom-color: #374151;
  background-color: #1f2937;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background-color: #f9fafb;
}

.dark .file-item:hover {
  background-color: #111827;
}
</style>
