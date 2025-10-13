<!-- src/pages/[type]s/[namespace]/[name]/settings.vue -->
<template>
  <div class="container-main">
    <!-- Breadcrumb Navigation -->
    <el-breadcrumb separator="/" class="mb-6 text-gray-700 dark:text-gray-300">
      <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s` }">
        {{
          repoType === "model"
            ? "Models"
            : repoType === "dataset"
              ? "Datasets"
              : "Spaces"
        }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${route.params.namespace}` }">
        {{ route.params.namespace }}
      </el-breadcrumb-item>
      <el-breadcrumb-item
        :to="{
          path: `/${repoType}s/${route.params.namespace}/${route.params.name}`,
        }"
      >
        {{ route.params.name }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>Settings</el-breadcrumb-item>
    </el-breadcrumb>

    <h1 class="text-3xl font-bold mb-6">
      Repository Settings: {{ route.params.name }}
    </h1>

    <el-tabs v-model="activeTab">
      <!-- General Settings -->
      <el-tab-pane label="General" name="general">
        <div class="max-w-2xl space-y-6">
          <!-- Visibility -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Visibility</h2>
            <el-form label-position="top">
              <el-form-item label="Repository Visibility">
                <div class="visibility-options">
                  <div
                    :class="[
                      'visibility-option',
                      { selected: !settings.private },
                    ]"
                    @click="settings.private = false"
                  >
                    <div class="option-radio">
                      <div
                        :class="[
                          'radio-circle',
                          { checked: !settings.private },
                        ]"
                      >
                        <div v-if="!settings.private" class="radio-dot" />
                      </div>
                    </div>
                    <div class="option-icon">
                      <div class="i-carbon-unlock text-xl" />
                    </div>
                    <div class="option-content">
                      <div class="option-title">Public</div>
                      <div class="option-description">
                        Anyone can see this repository
                      </div>
                    </div>
                  </div>

                  <div
                    :class="[
                      'visibility-option',
                      { selected: settings.private },
                    ]"
                    @click="settings.private = true"
                  >
                    <div class="option-radio">
                      <div
                        :class="['radio-circle', { checked: settings.private }]"
                      >
                        <div v-if="settings.private" class="radio-dot" />
                      </div>
                    </div>
                    <div class="option-icon">
                      <div class="i-carbon-locked text-xl" />
                    </div>
                    <div class="option-content">
                      <div class="option-title">Private</div>
                      <div class="option-description">
                        Only you and collaborators can see this repository
                      </div>
                    </div>
                  </div>
                </div>
              </el-form-item>

              <el-button type="primary" @click="saveGeneralSettings">
                Save Changes
              </el-button>
            </el-form>
          </div>

          <!-- Move/Rename Repository -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4 text-warning">
              Move/Rename Repository
            </h2>
            <p class="text-sm text-gray-600 mb-4">
              Moving a repository will redirect the old URL to the new one.
            </p>
            <el-form label-position="top">
              <el-form-item label="New Repository ID (namespace/name)">
                <el-input
                  v-model="moveToRepo"
                  placeholder="e.g., my-org/my-new-repo"
                />
              </el-form-item>
              <el-button type="warning" @click="handleMoveRepo">
                Move Repository
              </el-button>
            </el-form>
          </div>

          <!-- Danger Zone -->
          <div class="card border-2 border-red-500">
            <h2 class="text-xl font-semibold mb-4 text-red-600">Danger Zone</h2>
            <div class="space-y-4">
              <div>
                <h3 class="font-medium text-red-600 mb-2">
                  Delete this repository
                </h3>
                <p class="text-sm text-gray-600 mb-3">
                  Once you delete a repository, there is no going back. Please
                  be certain.
                </p>
                <el-button type="danger" @click="handleDeleteRepo">
                  Delete Repository
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Branches & Tags -->
      <el-tab-pane label="Branches & Tags" name="branches">
        <div class="max-w-2xl space-y-6">
          <!-- Branches -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Branches</h2>

            <!-- Create Branch -->
            <div class="mb-6">
              <h3 class="font-medium mb-3">Create New Branch</h3>
              <el-form inline>
                <el-form-item label="Branch Name">
                  <el-input
                    v-model="newBranch.name"
                    placeholder="my-feature-branch"
                  />
                </el-form-item>
                <el-form-item label="From Revision">
                  <el-input
                    v-model="newBranch.revision"
                    placeholder="main (default)"
                  />
                </el-form-item>
                <el-button type="primary" @click="handleCreateBranch">
                  Create Branch
                </el-button>
              </el-form>
            </div>
          </div>

          <!-- Tags -->
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Tags</h2>

            <!-- Create Tag -->
            <div class="mb-6">
              <h3 class="font-medium mb-3">Create New Tag</h3>
              <el-form label-position="top">
                <el-form-item label="Tag Name">
                  <el-input v-model="newTag.name" placeholder="v1.0.0" />
                </el-form-item>
                <el-form-item label="From Revision (optional)">
                  <el-input
                    v-model="newTag.revision"
                    placeholder="main (default)"
                  />
                </el-form-item>
                <el-form-item label="Message (optional)">
                  <el-input
                    v-model="newTag.message"
                    type="textarea"
                    placeholder="Release notes..."
                  />
                </el-form-item>
                <el-button type="primary" @click="handleCreateTag">
                  Create Tag
                </el-button>
              </el-form>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { repoAPI, settingsAPI } from "@/utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const activeTab = ref("general");
const settings = ref({
  private: false,
});
const moveToRepo = ref("");
const newBranch = ref({
  name: "",
  revision: "",
});
const newTag = ref({
  name: "",
  revision: "",
  message: "",
});

const repoId = computed(() => `${route.params.namespace}/${route.params.name}`);
const repoType = computed(() => route.params.type);

async function loadRepoInfo() {
  try {
    const { data } = await repoAPI.getInfo(
      repoType.value,
      route.params.namespace,
      route.params.name,
    );
    settings.value.private = data.private || false;
    moveToRepo.value = repoId.value;
  } catch (err) {
    console.error("Failed to load repo info:", err);
    ElMessage.error("Failed to load repository information");
  }
}

async function saveGeneralSettings() {
  try {
    await settingsAPI.updateRepoSettings(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        private: settings.value.private,
      },
    );
    ElMessage.success("Settings updated successfully");
  } catch (err) {
    console.error("Failed to update settings:", err);
    ElMessage.error("Failed to update settings");
  }
}

async function handleMoveRepo() {
  if (!moveToRepo.value || moveToRepo.value === repoId.value) {
    ElMessage.warning("Please enter a new repository ID");
    return;
  }

  try {
    await ElMessageBox.confirm(
      `This will move the repository to ${moveToRepo.value}. Old links will redirect to the new location. Continue?`,
      "Move Repository",
      {
        type: "warning",
        confirmButtonText: "Move",
        cancelButtonText: "Cancel",
      },
    );

    await settingsAPI.moveRepo({
      fromRepo: repoId.value,
      toRepo: moveToRepo.value,
      type: repoType.value,
    });

    ElMessage.success("Repository moved successfully");

    // Redirect to new location
    const [newNamespace, newName] = moveToRepo.value.split("/");
    router.push(`/${repoType.value}s/${newNamespace}/${newName}`);
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to move repository:", err);
      ElMessage.error("Failed to move repository");
    }
  }
}

async function handleDeleteRepo() {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete ${repoId.value}? This action cannot be undone!`,
      "Delete Repository",
      {
        type: "error",
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        confirmButtonClass: "el-button--danger",
      },
    );

    // Second confirmation
    await ElMessageBox.prompt(
      `Please type the repository name "${route.params.name}" to confirm`,
      "Confirm Deletion",
      {
        confirmButtonText: "Delete",
        cancelButtonText: "Cancel",
        inputPattern: new RegExp(`^${route.params.name}$`),
        inputErrorMessage: "Repository name does not match",
      },
    );

    await repoAPI.delete({
      type: repoType.value,
      name: route.params.name,
      organization: route.params.namespace,
    });

    ElMessage.success("Repository deleted successfully");
    router.push("/");
  } catch (err) {
    if (err !== "cancel" && err !== "close") {
      console.error("Failed to delete repository:", err);
      ElMessage.error("Failed to delete repository");
    }
  }
}

async function handleCreateBranch() {
  if (!newBranch.value.name) {
    ElMessage.warning("Please enter a branch name");
    return;
  }

  try {
    await settingsAPI.createBranch(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        branch: newBranch.value.name,
        revision: newBranch.value.revision || undefined,
      },
    );

    ElMessage.success(`Branch '${newBranch.value.name}' created successfully`);
    newBranch.value = { name: "", revision: "" };
  } catch (err) {
    console.error("Failed to create branch:", err);
    ElMessage.error("Failed to create branch");
  }
}

async function handleCreateTag() {
  if (!newTag.value.name) {
    ElMessage.warning("Please enter a tag name");
    return;
  }

  try {
    await settingsAPI.createTag(
      repoType.value,
      route.params.namespace,
      route.params.name,
      {
        tag: newTag.value.name,
        revision: newTag.value.revision || undefined,
        message: newTag.value.message || undefined,
      },
    );

    ElMessage.success(`Tag '${newTag.value.name}' created successfully`);
    newTag.value = { name: "", revision: "", message: "" };
  } catch (err) {
    console.error("Failed to create tag:", err);
    ElMessage.error("Failed to create tag");
  }
}

onMounted(() => {
  if (!authStore.isAuthenticated) {
    ElMessage.error("You must be logged in to access settings");
    router.push("/login");
    return;
  }
  loadRepoInfo();
});
</script>

<style scoped>
/* Visibility options container */
.visibility-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

/* Individual visibility option */
.visibility-option {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 0.75rem;
  align-items: start;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dark .visibility-option {
  border-color: #374151;
}

.visibility-option:hover {
  background-color: #f9fafb;
  border-color: #d1d5db;
}

.dark .visibility-option:hover {
  background-color: #1f2937;
  border-color: #4b5563;
}

.visibility-option.selected {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.dark .visibility-option.selected {
  border-color: #60a5fa;
  background-color: #1e3a8a;
}

/* Custom radio circle */
.option-radio {
  display: flex;
  align-items: center;
  padding-top: 0.125rem;
}

.radio-circle {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.dark .radio-circle {
  border-color: #6b7280;
}

.radio-circle.checked {
  border-color: #3b82f6;
  background-color: #3b82f6;
}

.dark .radio-circle.checked {
  border-color: #60a5fa;
  background-color: #60a5fa;
}

.radio-dot {
  width: 0.5rem;
  height: 0.5rem;
  background-color: white;
  border-radius: 50%;
}

/* Icon styling */
.option-icon {
  display: flex;
  align-items: center;
  color: #6b7280;
  padding-top: 0.125rem;
}

.dark .option-icon {
  color: #9ca3af;
}

.visibility-option.selected .option-icon {
  color: #3b82f6;
}

.dark .visibility-option.selected .option-icon {
  color: #60a5fa;
}

/* Content area */
.option-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.option-title {
  font-weight: 600;
  font-size: 0.9375rem;
  color: #111827;
  line-height: 1.4;
}

.dark .option-title {
  color: #f9fafb;
}

.option-description {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.4;
}

.dark .option-description {
  color: #9ca3af;
}
</style>
