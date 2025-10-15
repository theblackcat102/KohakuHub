<!-- src/kohaku-hub-ui/src/pages/settings.vue -->
<template>
  <div class="container-main">
    <h1 class="text-3xl font-bold mb-6">Settings</h1>

    <el-tabs v-model="activeTab">
      <!-- Profile -->
      <el-tab-pane label="Profile" name="profile">
        <div class="max-w-2xl">
          <!-- Avatar Section -->
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">Avatar</h2>
            <AvatarUpload
              entity-type="user"
              :entity-name="user?.username"
              :upload-function="settingsAPI.uploadUserAvatar"
              :delete-function="settingsAPI.deleteUserAvatar"
              @uploaded="avatarKey++"
              @deleted="avatarKey++"
            />
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Profile Information</h2>
            <el-form label-position="top">
              <el-form-item label="Username">
                <el-input :value="user?.username" disabled />
              </el-form-item>
              <el-form-item label="Email">
                <el-input v-model="profileForm.email" />
                <div
                  v-if="user?.email_verified"
                  class="text-sm text-green-600 mt-1"
                >
                  <div class="i-carbon-checkmark-filled inline-block" />
                  Verified
                </div>
                <div v-else class="text-sm text-yellow-600 mt-1">
                  <div class="i-carbon-warning inline-block" />
                  Not verified
                </div>
              </el-form-item>
              <el-form-item label="Full Name">
                <el-input
                  v-model="profileForm.full_name"
                  placeholder="Your full name"
                />
              </el-form-item>
              <el-form-item label="Bio">
                <el-input
                  v-model="profileForm.bio"
                  type="textarea"
                  :rows="3"
                  placeholder="A short bio about yourself"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
              <el-form-item label="Website">
                <el-input
                  v-model="profileForm.website"
                  placeholder="https://example.com"
                />
              </el-form-item>
              <el-form-item label="Social Media">
                <div class="space-y-2">
                  <el-input
                    v-model="profileForm.social_media.twitter_x"
                    placeholder="Twitter/X username"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-x w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.threads"
                    placeholder="Threads username"
                  >
                    <template #prepend>Threads</template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.github"
                    placeholder="GitHub username"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-github w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="profileForm.social_media.huggingface"
                    placeholder="HuggingFace username"
                  >
                    <template #prepend>🤗</template>
                  </el-input>
                </div>
              </el-form-item>
              <el-button
                type="primary"
                @click="updateProfile"
                :disabled="!hasProfileChanges"
              >
                Save Profile
              </el-button>
            </el-form>
          </div>

          <!-- Organizations -->
          <div class="card mt-4">
            <h2 class="text-xl font-semibold mb-4">Organizations</h2>
            <div v-if="userOrgs.length > 0" class="space-y-2">
              <div
                v-for="org in userOrgs"
                :key="org.name"
                class="flex items-center justify-between p-3 border rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                @click="goToOrganization(org.name)"
              >
                <div class="flex items-center gap-3">
                  <div class="i-carbon-group text-2xl text-gray-500" />
                  <div>
                    <div class="font-medium">{{ org.name }}</div>
                    <div class="text-sm text-gray-600">
                      {{ org.roleInOrg || org.role }}
                    </div>
                  </div>
                </div>
                <div class="i-carbon-arrow-right" />
              </div>
            </div>
            <div
              v-else
              class="text-center py-8 text-gray-500 dark:text-gray-400"
            >
              You're not a member of any organizations
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- API Tokens -->
      <el-tab-pane label="API Tokens" name="tokens">
        <div class="max-w-2xl">
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">Create New Token</h2>
            <div class="flex gap-2">
              <el-input
                v-model="newTokenName"
                placeholder="Token name (e.g., my-laptop)"
              />
              <el-button type="primary" @click="handleCreateToken">
                Create Token
              </el-button>
            </div>
          </div>

          <div v-if="newToken" class="card mb-4 bg-yellow-50">
            <h3 class="font-semibold mb-2">New Token Created</h3>
            <p class="text-sm text-gray-600 mb-2">
              Make sure to copy your token now. You won't be able to see it
              again!
            </p>
            <el-input :value="newToken" readonly class="font-mono">
              <template #append>
                <el-button @click="copyToken">
                  <div class="i-carbon-copy" />
                </el-button>
              </template>
            </el-input>
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Active Tokens</h2>
            <div class="space-y-2">
              <div
                v-for="token in tokens"
                :key="token.id"
                class="flex items-center justify-between p-3 border border-gray-200 rounded"
              >
                <div>
                  <div class="font-medium">{{ token.name }}</div>
                  <div class="text-sm text-gray-600">
                    Created {{ formatDate(token.created_at) }}
                  </div>
                </div>
                <el-button
                  type="danger"
                  text
                  @click="handleRevokeToken(token.id)"
                >
                  Revoke
                </el-button>
              </div>

              <div
                v-if="!tokens || tokens.length === 0"
                class="text-center py-8 text-gray-500"
              >
                No active tokens
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";
import { authAPI, settingsAPI } from "@/utils/api";
import { copyToClipboard } from "@/utils/clipboard";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";
import AvatarUpload from "@/components/profile/AvatarUpload.vue";

const router = useRouter();
const authStore = useAuthStore();
const { user } = storeToRefs(authStore);

const activeTab = ref("profile");
const newTokenName = ref("");
const newToken = ref("");
const tokens = ref([]);
const userOrgs = ref([]);
const avatarKey = ref(0); // Force re-render avatar on upload/delete
const profileForm = ref({
  email: "",
  full_name: "",
  bio: "",
  website: "",
  social_media: {
    twitter_x: "",
    threads: "",
    github: "",
    huggingface: "",
  },
});

const hasProfileChanges = computed(() => {
  if (!user.value) return false;
  return (
    profileForm.value.email !== user.value.email ||
    profileForm.value.full_name !== (user.value.full_name || "") ||
    profileForm.value.bio !== (user.value.bio || "") ||
    profileForm.value.website !== (user.value.website || "") ||
    JSON.stringify(profileForm.value.social_media) !==
      JSON.stringify(user.value.social_media || {})
  );
});

function formatDate(date) {
  return dayjs(date).format("MMM D, YYYY");
}

async function loadTokens() {
  try {
    const { data } = await authAPI.listTokens();
    tokens.value = data.tokens;
  } catch (err) {
    console.error("Failed to load tokens:", err);
  }
}

async function loadUserOrgs() {
  try {
    const { data } = await settingsAPI.whoamiV2();
    userOrgs.value = data.orgs || [];
  } catch (err) {
    console.error("Failed to load organizations:", err);
  }
}

async function updateProfile() {
  try {
    await settingsAPI.updateUserSettings(user.value.username, {
      email: profileForm.value.email,
      full_name: profileForm.value.full_name || null,
      bio: profileForm.value.bio || null,
      website: profileForm.value.website || null,
      social_media: profileForm.value.social_media,
    });
    ElMessage.success("Profile updated successfully");
    // Refresh user data
    await authStore.fetchUserInfo();
    // Update form with latest data
    loadUserProfile();
  } catch (err) {
    console.error("Failed to update profile:", err);
    ElMessage.error(err.response?.data?.detail || "Failed to update profile");
  }
}

async function loadUserProfile() {
  if (!user.value) return;

  try {
    const { data } = await settingsAPI.getUserProfile(user.value.username);
    profileForm.value.email = user.value.email;
    profileForm.value.full_name = data.full_name || "";
    profileForm.value.bio = data.bio || "";
    profileForm.value.website = data.website || "";
    profileForm.value.social_media = data.social_media || {
      twitter_x: "",
      threads: "",
      github: "",
      huggingface: "",
    };
  } catch (err) {
    console.error("Failed to load user profile:", err);
  }
}

function goToOrganization(orgName) {
  router.push(`/organizations/${orgName}`);
}

async function handleCreateToken() {
  if (!newTokenName.value) {
    ElMessage.warning("Please enter token name");
    return;
  }

  try {
    const { data } = await authAPI.createToken({ name: newTokenName.value });
    newToken.value = data.token;
    newTokenName.value = "";
    await loadTokens();
    ElMessage.success("Token created");
  } catch (err) {
    ElMessage.error("Failed to create token");
  }
}

async function handleRevokeToken(id) {
  try {
    await ElMessageBox.confirm(
      "This will permanently delete the token. Continue?",
      "Warning",
      { type: "warning" },
    );

    await authAPI.revokeToken(id);
    await loadTokens();
    ElMessage.success("Token revoked");
  } catch (err) {
    if (err !== "cancel") {
      ElMessage.error("Failed to revoke token");
    }
  }
}

async function copyToken() {
  const success = await copyToClipboard(newToken.value);
  if (success) {
    ElMessage.success("Token copied to clipboard");
  } else {
    ElMessage.error("Failed to copy token");
  }
}

onMounted(() => {
  loadUserProfile();
  loadTokens();
  loadUserOrgs();
});

watch(user, (newUser) => {
  if (newUser) {
    loadUserProfile();
  }
});
</script>
