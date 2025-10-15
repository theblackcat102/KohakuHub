<!-- src/components/profile/AvatarUpload.vue -->
<template>
  <div class="avatar-upload-container">
    <!-- Current Avatar Display -->
    <div class="flex flex-col sm:flex-row items-center sm:items-start gap-4">
      <div class="avatar-preview flex-shrink-0">
        <img
          v-if="currentAvatarUrl && !avatarError"
          :src="currentAvatarUrl"
          alt="Current avatar"
          class="w-24 h-24 rounded-full object-cover border-2 border-gray-200 dark:border-gray-600"
          @error="avatarError = true"
        />
        <div
          v-else
          class="w-24 h-24 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center border-2 border-gray-300 dark:border-gray-600"
        >
          <div
            :class="entityType === 'org' ? 'i-carbon-group' : 'i-carbon-user-avatar'"
            class="text-4xl text-gray-400"
          />
        </div>
      </div>

      <div class="flex-1 text-center sm:text-left">
        <div class="flex flex-col sm:flex-row gap-2 mb-2">
          <el-button size="small" @click="triggerFileInput">
            <div class="i-carbon-upload mr-1" />
            Upload Avatar
          </el-button>
          <el-button
            v-if="!avatarError"
            size="small"
            type="danger"
            @click="handleDelete"
          >
            <div class="i-carbon-trash-can mr-1" />
            Delete
          </el-button>
        </div>
        <div class="text-xs text-gray-500">
          Recommended: Square image, min 512x512px. Max 10MB.
        </div>
      </div>
    </div>

    <!-- Hidden file input -->
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/jpg,image/png,image/webp"
      style="display: none"
      @change="handleFileSelect"
    />

    <!-- Crop Dialog -->
    <el-dialog
      v-model="showCropDialog"
      title="Crop Avatar"
      width="700px"
      @close="resetCropper"
    >
      <div class="crop-container">
        <cropper-canvas
          ref="cropperCanvas"
          background
          scale-step="0.1"
          class="cropper-canvas-element"
        >
          <cropper-image
            ref="cropperImage"
            :src="imageSrc"
            alt="Crop preview"
            initial-center-size="contain"
            scalable
            translatable
          ></cropper-image>
          <cropper-shade hidden></cropper-shade>
          <cropper-handle action="select" plain></cropper-handle>
          <cropper-selection
            ref="cropperSelection"
            initial-coverage="1"
            aspect-ratio="1"
            movable
            resizable
            zoomable
          >
            <cropper-grid role="grid" covered></cropper-grid>
            <cropper-crosshair centered></cropper-crosshair>
            <cropper-handle action="move" theme-color="rgba(255, 255, 255, 0.5)"></cropper-handle>
            <cropper-handle action="n-resize"></cropper-handle>
            <cropper-handle action="e-resize"></cropper-handle>
            <cropper-handle action="s-resize"></cropper-handle>
            <cropper-handle action="w-resize"></cropper-handle>
            <cropper-handle action="ne-resize"></cropper-handle>
            <cropper-handle action="nw-resize"></cropper-handle>
            <cropper-handle action="se-resize"></cropper-handle>
            <cropper-handle action="sw-resize"></cropper-handle>
          </cropper-selection>
        </cropper-canvas>
      </div>

      <template #footer>
        <el-button @click="showCropDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleCrop" :loading="uploading">
          Upload Avatar
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import "cropperjs";
import { ElMessage, ElMessageBox } from "element-plus";

const props = defineProps({
  entityType: {
    type: String,
    required: true,
    validator: (value) => ["user", "org"].includes(value),
  },
  entityName: {
    type: String,
    required: true,
  },
  uploadFunction: {
    type: Function,
    required: true,
  },
  deleteFunction: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["uploaded", "deleted"]);

const fileInput = ref(null);
const cropperCanvas = ref(null);
const cropperSelection = ref(null);
const showCropDialog = ref(false);
const imageSrc = ref("");
const uploading = ref(false);
const avatarError = ref(false);
const avatarTimestamp = ref(Date.now());

const currentAvatarUrl = computed(() => {
  if (props.entityType === "user") {
    return `/api/users/${props.entityName}/avatar?t=${avatarTimestamp.value}`;
  } else {
    return `/api/organizations/${props.entityName}/avatar?t=${avatarTimestamp.value}`;
  }
});

function triggerFileInput() {
  fileInput.value?.click();
}

async function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Validate file type
  if (!["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(file.type)) {
    ElMessage.error("Only JPEG, PNG, and WebP images are supported");
    return;
  }

  // Validate file size (max 10MB)
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error("Image is too large. Maximum size is 10MB");
    return;
  }

  // Read file and show cropper
  const reader = new FileReader();
  reader.onload = (e) => {
    imageSrc.value = e.target.result;
    showCropDialog.value = true;
  };
  reader.readAsDataURL(file);

  // Clear input for re-selection
  event.target.value = "";
}

async function handleCrop() {
  if (!cropperSelection.value) {
    ElMessage.error("Cropper not initialized");
    return;
  }

  uploading.value = true;
  try {
    // Get cropped canvas from the selection (cropped area) instead of full canvas
    const canvas = await cropperSelection.value.$toCanvas({
      width: 1024,
      height: 1024,
    });

    if (!canvas) {
      throw new Error("Failed to get cropped canvas");
    }

    // Convert canvas to blob
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error("Failed to create blob"));
          }
        },
        "image/jpeg",
        0.95
      );
    });

    // Create file from blob
    const file = new File([blob], "avatar.jpg", { type: "image/jpeg" });

    // Upload
    await props.uploadFunction(props.entityName, file);

    ElMessage.success("Avatar uploaded successfully");
    showCropDialog.value = false;
    avatarError.value = false;
    avatarTimestamp.value = Date.now();
    emit("uploaded");
  } catch (error) {
    console.error("Failed to upload avatar:", error);
    ElMessage.error(error.response?.data?.detail || "Failed to upload avatar");
  } finally {
    uploading.value = false;
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      "Delete avatar? This action cannot be undone.",
      "Confirm Delete",
      {
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        type: "warning",
      }
    );

    await props.deleteFunction(props.entityName);
    ElMessage.success("Avatar deleted successfully");
    avatarError.value = true;
    emit("deleted");
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      console.error("Failed to delete avatar:", error);
      ElMessage.error("Failed to delete avatar");
    }
  }
}

function resetCropper() {
  imageSrc.value = "";
}
</script>

<style scoped>
.avatar-upload-container {
  width: 100%;
}

.crop-container {
  width: 100%;
  height: 500px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.cropper-canvas-element {
  width: 100%;
  height: 500px;
  display: block;
}

/* Make selection circular */
:deep(cropper-selection) {
  border-radius: 50%;
}
</style>
