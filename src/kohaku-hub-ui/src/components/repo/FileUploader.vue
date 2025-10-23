<!-- src/components/repo/FileUploader.vue -->
<template>
  <div class="file-uploader">
    <!-- File Drop Zone -->
    <div
      class="upload-zone"
      :class="{ 'is-dragover': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="$refs.fileInput.click()"
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
        <el-button type="primary" @click.stop="$refs.fileInput.click()">
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
        <div v-for="(fileItem, index) in files" :key="index" class="file-item">
          <div class="flex items-center gap-3 flex-1">
            <div class="i-carbon-document text-2xl text-blue-500" />
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{{ fileItem.file.name }}</div>
              <div class="text-sm text-gray-500 dark:text-gray-400">
                {{ formatFileSize(fileItem.file.size) }}
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
          <el-button size="small" text @click="removeFile(index)" class="ml-2">
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
        <!-- Progress header (changes based on stage) -->
        <div
          class="text-sm font-medium mb-2"
          :class="
            isHashing
              ? 'text-blue-600 dark:text-blue-400'
              : 'text-green-600 dark:text-green-400'
          "
        >
          {{
            isHashing
              ? `Calculating SHA256: ${hashingFileName}`
              : `Uploading: ${currentFileName}`
          }}
        </div>

        <!-- Single progress bar (color changes based on stage) -->
        <el-progress
          :percentage="isHashing ? hashingProgress : uploadProgress"
          :status="uploadStatus"
          :color="isHashing ? '#409eff' : '#67c23a'"
          :show-text="true"
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { repoAPI } from "@/utils/api";
import { formatFileSize } from "@/utils/lfs";

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
});

const emit = defineEmits(["upload-success", "upload-error"]);

// State
const files = ref([]);
const isDragging = ref(false);
const uploading = ref(false);
const isHashing = ref(false);
const hashingProgress = ref(0);
const hashingFileName = ref("");
const uploadProgress = ref(0);
const uploadStatus = ref("");
const currentFileName = ref("");
const fileInput = ref(null);

const commitForm = ref({
  message: "Upload files via web interface",
  description: "",
});

// Computed
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
  isHashing.value = false;
  hashingProgress.value = 0;
  hashingFileName.value = "";
  uploadProgress.value = 0;
  uploadStatus.value = "";
  currentFileName.value = "";
}

async function handleUpload() {
  if (!canUpload.value) return;

  uploading.value = true;
  isHashing.value = true;
  hashingProgress.value = 0;
  uploadProgress.value = 0;
  uploadStatus.value = "";

  try {
    await repoAPI.uploadFiles(
      props.repoType,
      props.namespace,
      props.name,
      props.branch,
      {
        files: files.value,
        message: commitForm.value.message,
        description: commitForm.value.description,
      },
      {
        onHashProgress: (fileName, progress) => {
          isHashing.value = true;
          hashingFileName.value = fileName;
          hashingProgress.value = Math.round(progress * 100);
        },
        onUploadProgress: (fileName, progress) => {
          isHashing.value = false;
          currentFileName.value = fileName;
          uploadProgress.value = Math.round(progress * 100);
        },
      },
    );

    uploadStatus.value = "success";
    ElMessage.success("Files uploaded successfully");
    emit("upload-success");

    // Clear form after short delay
    setTimeout(() => {
      clearFiles();
      commitForm.value.message = "Upload files via web interface";
      commitForm.value.description = "";
    }, 1000);
  } catch (err) {
    uploadStatus.value = "exception";
    const errorMsg = err.response?.data?.detail || "Failed to upload files";
    ElMessage.error(errorMsg);
    emit("upload-error", err);
    console.error("Upload error:", err);
  } finally {
    uploading.value = false;
  }
}

// Expose methods
defineExpose({
  clearFiles,
  handleUpload,
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
