<!-- src/kohaku-hub-ui/src/pages/invite/[token].vue -->
<template>
  <div class="container-main">
    <div class="max-w-2xl mx-auto">
      <!-- Loading State -->
      <div v-if="loading" class="card text-center py-12">
        <el-skeleton :rows="5" animated />
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="card text-center py-12">
        <div class="i-carbon-warning text-6xl text-red-500 mb-4 inline-block" />
        <h2 class="text-2xl font-bold text-red-600 mb-2">Invalid Invitation</h2>
        <p class="text-gray-600 dark:text-gray-400 mb-4">{{ error }}</p>
        <el-button type="primary" @click="$router.push('/')">
          Go to Home
        </el-button>
      </div>

      <!-- Invitation Details -->
      <div v-else-if="invitation" class="card">
        <!-- Header -->
        <div class="text-center mb-6">
          <div class="i-carbon-email text-6xl text-blue-500 mb-4 inline-block" />
          <h1 class="text-3xl font-bold mb-2">Organization Invitation</h1>
          <p class="text-gray-600 dark:text-gray-400">
            You've been invited to join an organization
          </p>
        </div>

        <!-- Invitation Info -->
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-6 mb-6">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-gray-600 dark:text-gray-400">Organization:</span>
              <span class="font-semibold text-lg">{{ invitation.org_name }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-600 dark:text-gray-400">Role:</span>
              <el-tag :type="getRoleType(invitation.role)">
                {{ getRoleLabel(invitation.role) }}
              </el-tag>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-600 dark:text-gray-400">Invited by:</span>
              <span class="font-medium">{{ invitation.inviter_username }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-gray-600 dark:text-gray-400">Expires:</span>
              <span>{{ formatDate(invitation.expires_at) }}</span>
            </div>
            <div
              v-if="invitation.is_reusable"
              class="flex items-center justify-between"
            >
              <span class="text-gray-600 dark:text-gray-400">Type:</span>
              <el-tag type="success" size="small">Reusable Link</el-tag>
            </div>
            <div
              v-if="invitation.is_reusable"
              class="flex items-center justify-between"
            >
              <span class="text-gray-600 dark:text-gray-400">Usage:</span>
              <span class="font-mono text-sm">
                {{ invitation.usage_count }} /
                {{
                  invitation.max_usage === -1
                    ? "Unlimited"
                    : invitation.max_usage
                }}
              </span>
            </div>
          </div>
        </div>

        <!-- Error Warning (Expired/Max Usage) -->
        <div
          v-if="!invitation.is_available"
          class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6"
        >
          <div class="flex items-start gap-3">
            <div class="i-carbon-warning text-xl text-yellow-600" />
            <div>
              <h3 class="font-semibold text-yellow-800 dark:text-yellow-200">
                Invitation Unavailable
              </h3>
              <p class="text-sm text-yellow-700 dark:text-yellow-300">
                {{ invitation.error_message || "This invitation is no longer available." }}
              </p>
            </div>
          </div>
        </div>

        <!-- Usage Info for Reusable Links -->
        <div
          v-else-if="invitation.is_reusable && invitation.usage_count > 0"
          class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6"
        >
          <div class="flex items-start gap-3">
            <div class="i-carbon-information text-xl text-blue-600" />
            <div>
              <h3 class="font-semibold text-blue-800 dark:text-blue-200">
                Reusable Invitation
              </h3>
              <p class="text-sm text-blue-700 dark:text-blue-300">
                This link has been used {{ invitation.usage_count }} time{{
                  invitation.usage_count !== 1 ? "s" : ""
                }}. You can still use it to join the organization.
              </p>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-center gap-3">
          <!-- Not logged in -->
          <template v-if="!authStore.isAuthenticated">
            <el-button type="primary" size="large" @click="goToLogin">
              Log In to Accept
            </el-button>
            <el-button size="large" @click="goToRegister">
              Create Account
            </el-button>
          </template>

          <!-- Logged in and can accept -->
          <template v-else-if="invitation.is_available">
            <el-button
              type="primary"
              size="large"
              @click="acceptInvitation"
              :loading="accepting"
            >
              Accept Invitation
            </el-button>
            <el-button size="large" @click="$router.push('/')">
              Decline
            </el-button>
          </template>

          <!-- Cannot accept -->
          <template v-else>
            <el-button type="primary" size="large" @click="$router.push('/')">
              Go to Home
            </el-button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { invitationAPI } from "@/utils/api";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const loading = ref(true);
const accepting = ref(false);
const invitation = ref(null);
const error = ref(null);

function formatDate(date) {
  return dayjs(date).format("MMM D, YYYY [at] h:mm A");
}

function getRoleType(role) {
  switch (role) {
    case "super-admin":
      return "danger";
    case "admin":
      return "warning";
    case "member":
      return "info";
    case "visitor":
      return "";
    default:
      return "";
  }
}

function getRoleLabel(role) {
  switch (role) {
    case "visitor":
      return "Visitor (Read-only)";
    case "member":
      return "Member";
    case "admin":
      return "Admin";
    case "super-admin":
      return "Super Admin";
    default:
      return role;
  }
}

function goToLogin() {
  const returnUrl = encodeURIComponent(route.fullPath);
  router.push(`/login?return=${returnUrl}`);
}

function goToRegister() {
  const returnUrl = encodeURIComponent(route.fullPath);
  router.push(`/register?return=${returnUrl}`);
}

async function loadInvitation() {
  loading.value = true;
  error.value = null;

  try {
    const { data } = await invitationAPI.get(route.params.token);
    invitation.value = data;
  } catch (err) {
    console.error("Failed to load invitation:", err);
    if (err.response?.status === 404) {
      error.value = "Invitation not found. It may have been deleted or is invalid.";
    } else {
      error.value = "Failed to load invitation details.";
    }
  } finally {
    loading.value = false;
  }
}

async function acceptInvitation() {
  if (!authStore.isAuthenticated) {
    goToLogin();
    return;
  }

  accepting.value = true;
  try {
    const { data } = await invitationAPI.accept(route.params.token);
    ElMessage.success(data.message);

    // Redirect to organization page
    setTimeout(() => {
      router.push(`/organizations/${data.org_name}`);
    }, 1500);
  } catch (err) {
    console.error("Failed to accept invitation:", err);
    const detail = err.response?.data?.detail;

    if (typeof detail === "string") {
      ElMessage.error(detail);
    } else if (detail?.error) {
      ElMessage.error(detail.error);
    } else {
      ElMessage.error("Failed to accept invitation");
    }

    // Reload invitation to get updated status
    await loadInvitation();
  } finally {
    accepting.value = false;
  }
}

onMounted(() => {
  loadInvitation();
});
</script>
