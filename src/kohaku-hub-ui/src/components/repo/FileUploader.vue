<!-- src/components/repo/FileUploader.vue -->
<template>
  <div class="file-uploader">
    <el-upload
      ref="uploadRef"
      :action="uploadUrl"
      :headers="uploadHeaders"
      :data="uploadData"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-progress="handleProgress"
      :show-file-list="true"
      :file-list="fileList"
      :multiple="true"
      :drag="true"
      :auto-upload="false"
      class="upload-demo"
    >
      <div class="upload-area">
        <div class="i-carbon-cloud-upload text-6xl text-gray-400 mb-4" />
        <div class="text-lg font-medium mb-2">
          Drop files here or click to upload
        </div>
        <div class="text-sm text-gray-500">
          You can upload multiple files at once
        </div>
      </div>
    </el-upload>

    <div v-if="fileList.length > 0" class="mt-4">
      <div class="flex items-center justify-between mb-3">
        <div class="text-sm text-gray-600 dark:text-gray-400">
          {{ fileList.length }} file(s) selected
        </div>
        <div class="flex gap-2">
          <el-button size="small" @click="clearFiles">Clear All</el-button>
          <el-button
            type="primary"
            size="small"
            :loading="uploading"
            :disabled="fileList.length === 0"
            @click="submitUpload"
          >
            <div v-if="!uploading" class="i-carbon-upload inline-block mr-1" />
            {{ uploading ? `Uploading... ${uploadProgress}%` : "Upload Files" }}
          </el-button>
        </div>
      </div>

      <!-- Upload Path Input -->
      <div class="mb-3">
        <label class="block text-sm font-medium mb-1">Upload to path:</label>
        <el-input
          v-model="uploadPath"
          placeholder="Leave empty for root, or enter folder path (e.g., data/images)"
          size="small"
        >
          <template #prepend>/</template>
        </el-input>
      </div>

      <!-- Commit Message -->
      <div class="mb-3">
        <label class="block text-sm font-medium mb-1">Commit message:</label>
        <el-input
          v-model="commitMessage"
          type="textarea"
          :rows="2"
          placeholder="Add files via upload"
          size="small"
        />
      </div>
    </div>

    <!-- Upload Progress -->
    <div v-if="uploading" class="mt-4">
      <el-progress :percentage="uploadProgress" :status="uploadStatus" />
      <div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
        {{ currentFileName }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import { repoAPI } from "@/utils/api";

const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
  currentPath: { type: String, default: "" },
});

const emit = defineEmits(["upload-success", "upload-error"]);

const authStore = useAuthStore();
const uploadRef = ref(null);
const fileList = ref([]);
const uploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref("");
const currentFileName = ref("");
const uploadPath = ref(props.currentPath || "");
const commitMessage = ref("Add files via upload");

const uploadUrl = computed(() => {
  return `/api/${props.repoType}s/${props.namespace}/${props.name}/commit/${props.branch}`;
});

const uploadHeaders = computed(() => {
  return {
    Authorization: `Bearer ${authStore.token}`,
  };
});

const uploadData = computed(() => {
  return {
    message: commitMessage.value,
    path: uploadPath.value,
  };
});

function beforeUpload(file) {
  const maxSize = 100 * 1024 * 1024; // 100MB per file for regular upload
  if (file.size > maxSize) {
    ElMessage.warning(
      `File ${file.name} is too large. Maximum size is 100MB per file.`,
    );
    return false;
  }
  return true;
}

async function submitUpload() {
  if (fileList.value.length === 0) {
    ElMessage.warning("Please select files to upload");
    return;
  }

  if (!commitMessage.value.trim()) {
    ElMessage.warning("Please enter a commit message");
    return;
  }

  uploading.value = true;
  uploadProgress.value = 0;
  uploadStatus.value = "";

  try {
    // Use HuggingFace Hub API commit format
    const files = fileList.value.map((file) => ({
      path: uploadPath.value ? `${uploadPath.value}/${file.name}` : file.name,
      file: file.raw,
    }));

    // Upload files using the repo API
    await repoAPI.uploadFiles(
      props.repoType,
      props.namespace,
      props.name,
      props.branch,
      {
        files,
        message: commitMessage.value,
      },
      (progress) => {
        uploadProgress.value = Math.round(progress * 100);
      },
    );

    uploadStatus.value = "success";
    ElMessage.success("Files uploaded successfully");
    emit("upload-success");

    // Clear form
    setTimeout(() => {
      clearFiles();
      commitMessage.value = "Add files via upload";
    }, 1000);
  } catch (error) {
    uploadStatus.value = "exception";
    const errorMsg = error.response?.data?.detail || "Upload failed";
    ElMessage.error(errorMsg);
    emit("upload-error", error);
  } finally {
    uploading.value = false;
  }
}

function handleSuccess(response, file) {
  ElMessage.success(`${file.name} uploaded successfully`);
}

function handleError(error, file) {
  ElMessage.error(`${file.name} upload failed`);
  console.error("Upload error:", error);
}

function handleProgress(event, file) {
  currentFileName.value = `Uploading ${file.name}...`;
  uploadProgress.value = Math.round(event.percent);
}

function clearFiles() {
  uploadRef.value?.clearFiles();
  fileList.value = [];
  uploadProgress.value = 0;
  uploadStatus.value = "";
  currentFileName.value = "";
}

// Expose methods
defineExpose({
  clearFiles,
  submitUpload,
});
</script>

<style scoped>
.upload-area {
  padding: 60px 20px;
  text-align: center;
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.3s;
}

.upload-area:hover {
  border-color: #409eff;
}

:global(.dark) .upload-area {
  border-color: #4c4d4f;
  background-color: rgba(255, 255, 255, 0.02);
}

:global(.dark) .upload-area:hover {
  border-color: #409eff;
}

.upload-demo :deep(.el-upload-dragger) {
  border: none;
  background: transparent;
  padding: 0;
}

.upload-demo :deep(.el-upload-dragger:hover) {
  border: none;
}
</style>
