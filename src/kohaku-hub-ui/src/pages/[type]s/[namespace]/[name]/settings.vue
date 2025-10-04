<!-- src/pages/[type]s/[namespace]/[name]/settings.vue -->
<template>
  <div class="container-main">
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
                <el-radio-group v-model="settings.private">
                  <el-radio :label="false">
                    <div class="flex items-center gap-2">
                      <div class="i-carbon-unlock" />
                      <div>
                        <div class="font-medium">Public</div>
                        <div class="text-sm text-gray-500">
                          Anyone can see this repository
                        </div>
                      </div>
                    </div>
                  </el-radio>
                  <el-radio :label="true">
                    <div class="flex items-center gap-2">
                      <div class="i-carbon-locked" />
                      <div>
                        <div class="font-medium">Private</div>
                        <div class="text-sm text-gray-500">
                          Only you and collaborators can see this repository
                        </div>
                      </div>
                    </div>
                  </el-radio>
                </el-radio-group>
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

    const { data } = await settingsAPI.moveRepo({
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
    const { value } = await ElMessageBox.prompt(
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
