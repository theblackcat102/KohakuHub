<!-- src/kohaku-hub-ui/src/pages/organizations/[org]/settings.vue -->
<template>
  <div class="container-main">
    <div class="mb-6">
      <router-link
        :to="`/organizations/${$route.params.org}`"
        class="text-blue-600 hover:underline"
      >
        ← Back to {{ $route.params.org }}
      </router-link>
    </div>

    <h1 class="text-3xl font-bold mb-6">Organization Settings</h1>

    <el-tabs v-model="activeTab">
      <!-- General Settings Tab -->
      <el-tab-pane label="General" name="general">
        <div class="max-w-2xl">
          <!-- Avatar Section -->
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">Organization Avatar</h2>
            <AvatarUpload
              entity-type="org"
              :entity-name="$route.params.org"
              :upload-function="settingsAPI.uploadOrgAvatar"
              :delete-function="settingsAPI.deleteOrgAvatar"
              @uploaded="avatarKey++"
              @deleted="avatarKey++"
            />
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Organization Profile</h2>
            <el-form label-position="top">
              <el-form-item label="Organization Name">
                <el-input :value="$route.params.org" disabled />
                <div class="text-sm text-gray-500 mt-1">
                  Organization name cannot be changed
                </div>
              </el-form-item>

              <el-form-item label="Description">
                <el-input
                  v-model="generalForm.description"
                  type="textarea"
                  :rows="3"
                  placeholder="A short description of your organization"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="Bio">
                <el-input
                  v-model="generalForm.bio"
                  type="textarea"
                  :rows="3"
                  placeholder="Additional details about your organization"
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="Website">
                <el-input
                  v-model="generalForm.website"
                  placeholder="https://example.com"
                />
              </el-form-item>

              <el-form-item label="Social Media">
                <div class="space-y-2">
                  <el-input
                    v-model="generalForm.social_media.twitter_x"
                    placeholder="Twitter/X username"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-x w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="generalForm.social_media.threads"
                    placeholder="Threads username"
                  >
                    <template #prepend>Threads</template>
                  </el-input>
                  <el-input
                    v-model="generalForm.social_media.github"
                    placeholder="GitHub username"
                  >
                    <template #prepend>
                      <div class="i-carbon-logo-github w-4 h-4" />
                    </template>
                  </el-input>
                  <el-input
                    v-model="generalForm.social_media.huggingface"
                    placeholder="HuggingFace username"
                  >
                    <template #prepend>🤗</template>
                  </el-input>
                </div>
              </el-form-item>

              <el-button
                type="primary"
                @click="saveGeneralSettings"
                :disabled="!hasGeneralChanges"
                :loading="saving"
              >
                Save Changes
              </el-button>
            </el-form>
          </div>
        </div>
      </el-tab-pane>

      <!-- Members Tab -->
      <el-tab-pane label="Members" name="members">
        <div class="max-w-4xl">
          <div class="card mb-4">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold">Organization Members</h2>
              <el-button type="primary" @click="showInviteDialog = true">
                <div class="i-carbon-add mr-2" />
                Invite Member
              </el-button>
            </div>

            <div v-if="loadingMembers" class="text-center py-8">
              <el-skeleton :rows="3" animated />
            </div>

            <div v-else class="space-y-2">
              <div
                v-for="member in members"
                :key="member.user"
                class="flex items-center justify-between p-4 border rounded hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <div class="flex items-center gap-3">
                  <div class="i-carbon-user-avatar text-2xl text-gray-500" />
                  <div>
                    <router-link
                      :to="`/${member.user}`"
                      class="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {{ member.user }}
                    </router-link>
                    <div>
                      <el-tag size="small" :type="getRoleType(member.role)">
                        {{ member.role }}
                      </el-tag>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-2">
                  <el-select
                    v-model="member.role"
                    size="small"
                    @change="updateMemberRole(member.user, member.role)"
                    :disabled="member.role === 'super-admin'"
                  >
                    <el-option label="Visitor" value="visitor" />
                    <el-option label="Member" value="member" />
                    <el-option label="Admin" value="admin" />
                    <el-option
                      v-if="member.role === 'super-admin'"
                      label="Super Admin"
                      value="super-admin"
                      disabled
                    />
                  </el-select>

                  <el-button
                    type="danger"
                    text
                    size="small"
                    @click="removeMember(member.user)"
                    :disabled="member.role === 'super-admin'"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Invitations Tab -->
      <el-tab-pane label="Invitations" name="invitations">
        <div class="max-w-4xl">
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Pending Invitations</h2>

            <div v-if="loadingInvitations" class="text-center py-8">
              <el-skeleton :rows="3" animated />
            </div>

            <div v-else-if="invitations.length > 0" class="space-y-2">
              <div
                v-for="invite in invitations"
                :key="invite.id"
                class="flex items-center justify-between p-4 border rounded"
              >
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-medium">
                      {{ invite.email || "General Link" }}
                    </span>
                    <el-tag
                      v-if="invite.is_reusable"
                      size="small"
                      type="success"
                    >
                      Reusable
                    </el-tag>
                  </div>
                  <div class="text-sm text-gray-600 dark:text-gray-400">
                    Role: {{ invite.role }} • Created by {{ invite.created_by }}
                  </div>
                  <div class="text-sm text-gray-500">
                    Expires: {{ formatDate(invite.expires_at) }}
                  </div>
                  <div
                    v-if="invite.is_reusable"
                    class="text-sm text-gray-600 dark:text-gray-400"
                  >
                    Usage: {{ invite.usage_count }} /
                    {{
                      invite.max_usage === -1
                        ? "Unlimited"
                        : invite.max_usage || "1"
                    }}
                  </div>
                  <div v-if="!invite.is_available" class="text-sm text-red-600">
                    {{ getInvitationStatus(invite) }}
                  </div>
                  <div
                    v-else-if="invite.usage_count > 0"
                    class="text-sm text-green-600"
                  >
                    ✓ Used {{ invite.usage_count }} time{{
                      invite.usage_count !== 1 ? "s" : ""
                    }}
                  </div>
                </div>

                <div class="flex items-center gap-2">
                  <el-button
                    size="small"
                    @click="copyInvitationLink(invite.token)"
                  >
                    <div class="i-carbon-copy mr-1" />
                    Copy Link
                  </el-button>
                  <el-button
                    v-if="invite.is_available || invite.is_reusable"
                    type="danger"
                    text
                    size="small"
                    @click="deleteInvitation(invite.token)"
                  >
                    Delete
                  </el-button>
                </div>
              </div>
            </div>

            <div v-else class="text-center py-8 text-gray-500">
              No pending invitations
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Invite Member Dialog -->
    <el-dialog
      v-model="showInviteDialog"
      :title="
        inviteForm.type === 'reusable'
          ? 'Generate Invitation Link'
          : 'Invite Member'
      "
      width="550px"
      @close="resetInviteDialog"
    >
      <el-form label-position="top">
        <el-form-item>
          <el-radio-group
            v-model="inviteForm.type"
            @change="generatedLink = ''"
          >
            <el-radio-button label="single">
              Single-Use (Email)
            </el-radio-button>
            <el-radio-button label="reusable"> Reusable Link </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="inviteForm.type === 'single'" label="Email Address">
          <el-input
            v-model="inviteForm.email"
            placeholder="member@example.com"
          />
        </el-form-item>

        <el-form-item label="Role">
          <el-select v-model="inviteForm.role" style="width: 100%">
            <el-option label="Visitor (Read-only)" value="visitor" />
            <el-option label="Member" value="member" />
            <el-option label="Admin" value="admin" />
          </el-select>
        </el-form-item>

        <div v-if="inviteForm.type === 'reusable'">
          <el-form-item label="Maximum Usage">
            <el-select v-model="inviteForm.max_usage" style="width: 100%">
              <el-option label="Unlimited" :value="-1" />
              <el-option label="1 use" :value="1" />
              <el-option label="5 uses" :value="5" />
              <el-option label="10 uses" :value="10" />
              <el-option label="25 uses" :value="25" />
              <el-option label="50 uses" :value="50" />
              <el-option label="100 uses" :value="100" />
            </el-select>
          </el-form-item>

          <el-form-item label="Expires In">
            <el-select v-model="inviteForm.expires_days" style="width: 100%">
              <el-option label="1 day" :value="1" />
              <el-option label="3 days" :value="3" />
              <el-option label="7 days" :value="7" />
              <el-option label="14 days" :value="14" />
              <el-option label="30 days" :value="30" />
              <el-option label="90 days" :value="90" />
              <el-option label="365 days" :value="365" />
            </el-select>
          </el-form-item>

          <!-- Generated Link Display -->
          <el-form-item v-if="generatedLink" label="Invitation Link">
            <el-input :value="generatedLink" readonly class="font-mono text-sm">
              <template #append>
                <el-button @click="copyGeneratedLink">
                  <div class="i-carbon-copy" />
                </el-button>
              </template>
            </el-input>
            <div class="text-sm text-gray-500 mt-1">
              Share this link anywhere. Usage: 0 /
              {{
                inviteForm.max_usage === -1 ? "Unlimited" : inviteForm.max_usage
              }}
            </div>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="closeInviteDialog">
          {{ generatedLink ? "Done" : "Cancel" }}
        </el-button>
        <el-button
          v-if="!generatedLink"
          type="primary"
          @click="sendInvitation"
          :loading="inviting"
        >
          {{
            inviteForm.type === "reusable" ? "Generate Link" : "Send Invitation"
          }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from "vue-router";
import { orgAPI, invitationAPI, settingsAPI } from "@/utils/api";
import { copyToClipboard } from "@/utils/clipboard";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";
import AvatarUpload from "@/components/profile/AvatarUpload.vue";

const route = useRoute();
const router = useRouter();

const activeTab = ref("general");
const saving = ref(false);
const loadingMembers = ref(false);
const loadingInvitations = ref(false);
const inviting = ref(false);
const showInviteDialog = ref(false);
const avatarKey = ref(0); // Force re-render avatar

const originalProfile = ref(null);
const generalForm = ref({
  description: "",
  bio: "",
  website: "",
  social_media: {
    twitter_x: "",
    threads: "",
    github: "",
    huggingface: "",
  },
});

const members = ref([]);
const invitations = ref([]);

const inviteForm = ref({
  type: "single", // 'single' or 'reusable'
  email: "",
  role: "member",
  max_usage: 10,
  expires_days: 7,
});

const generatedLink = ref("");

const hasGeneralChanges = computed(() => {
  if (!originalProfile.value) return false;
  return (
    JSON.stringify(generalForm.value) !== JSON.stringify(originalProfile.value)
  );
});

function formatDate(date) {
  return dayjs(date).format("MMM D, YYYY");
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

function getInvitationStatus(invite) {
  if (!invite.is_available) {
    if (invite.usage_count >= (invite.max_usage || 1)) {
      return "Maximum usage reached";
    }
    return "Expired or unavailable";
  }
  return "";
}

async function loadOrgProfile() {
  try {
    const { data } = await settingsAPI.getOrgProfile(route.params.org);

    const profile = {
      description: data.description || "",
      bio: data.bio || "",
      website: data.website || "",
      social_media: data.social_media || {
        twitter_x: "",
        threads: "",
        github: "",
        huggingface: "",
      },
    };

    generalForm.value = JSON.parse(JSON.stringify(profile));
    originalProfile.value = JSON.parse(JSON.stringify(profile));
  } catch (err) {
    console.error("Failed to load organization profile:", err);
    ElMessage.error("Failed to load organization profile");
  }
}

async function saveGeneralSettings() {
  saving.value = true;
  try {
    await orgAPI.updateSettings(route.params.org, {
      description: generalForm.value.description || null,
      bio: generalForm.value.bio || null,
      website: generalForm.value.website || null,
      social_media: generalForm.value.social_media,
    });
    ElMessage.success("Settings saved successfully");
    await loadOrgProfile(); // Reload to sync
  } catch (err) {
    console.error("Failed to save settings:", err);
    ElMessage.error(err.response?.data?.detail || "Failed to save settings");
  } finally {
    saving.value = false;
  }
}

async function loadMembers() {
  loadingMembers.value = true;
  try {
    const { data } = await orgAPI.listMembers(route.params.org);
    members.value = data.members;
  } catch (err) {
    console.error("Failed to load members:", err);
    ElMessage.error("Failed to load members");
  } finally {
    loadingMembers.value = false;
  }
}

async function updateMemberRole(username, newRole) {
  try {
    await orgAPI.updateMemberRole(route.params.org, username, {
      role: newRole,
    });
    ElMessage.success(`Updated ${username}'s role to ${newRole}`);
  } catch (err) {
    console.error("Failed to update role:", err);
    ElMessage.error("Failed to update role");
    // Reload members to revert UI
    await loadMembers();
  }
}

async function removeMember(username) {
  try {
    await ElMessageBox.confirm(
      `Remove ${username} from this organization?`,
      "Confirm",
      { type: "warning" },
    );

    await orgAPI.removeMember(route.params.org, username);
    ElMessage.success(`${username} removed successfully`);
    await loadMembers();
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to remove member:", err);
      ElMessage.error("Failed to remove member");
    }
  }
}

function closeInviteDialog() {
  showInviteDialog.value = false;
  resetInviteDialog();
}

function resetInviteDialog() {
  inviteForm.value = {
    type: "single",
    email: "",
    role: "member",
    max_usage: 10,
    expires_days: 7,
  };
  generatedLink.value = "";
}

async function copyGeneratedLink() {
  const success = await copyToClipboard(generatedLink.value);
  if (success) {
    ElMessage.success("Invitation link copied to clipboard");
  } else {
    ElMessage.error("Failed to copy link");
  }
}

async function sendInvitation() {
  // Validate based on invitation type
  if (inviteForm.value.type === "single" && !inviteForm.value.email) {
    ElMessage.warning(
      "Please enter an email address for single-use invitation",
    );
    return;
  }

  inviting.value = true;
  try {
    const payload = {
      role: inviteForm.value.role,
    };

    // Add type-specific fields
    if (inviteForm.value.type === "single") {
      payload.email = inviteForm.value.email;
    } else {
      // Reusable invitation
      payload.max_usage = inviteForm.value.max_usage;
      payload.expires_days = inviteForm.value.expires_days;
    }

    const { data } = await invitationAPI.create(route.params.org, payload);

    if (inviteForm.value.type === "reusable") {
      // For reusable links, show in dialog
      generatedLink.value = data.invitation_link;
      ElMessage.success("Invitation link generated successfully");
    } else {
      // For single-use, close dialog and show success
      ElMessage.success("Invitation sent successfully");
      closeInviteDialog();
    }

    await loadInvitations();
  } catch (err) {
    console.error("Failed to send invitation:", err);
    ElMessage.error(err.response?.data?.detail || "Failed to send invitation");
  } finally {
    inviting.value = false;
  }
}

async function loadInvitations() {
  loadingInvitations.value = true;
  try {
    const { data } = await invitationAPI.list(route.params.org);
    invitations.value = data.invitations;
  } catch (err) {
    console.error("Failed to load invitations:", err);
    ElMessage.error("Failed to load invitations");
  } finally {
    loadingInvitations.value = false;
  }
}

async function copyInvitationLink(token) {
  const link = `${window.location.origin}/invite/${token}`;
  const success = await copyToClipboard(link);
  if (success) {
    ElMessage.success("Invitation link copied to clipboard");
  } else {
    ElMessage.error("Failed to copy link");
  }
}

async function deleteInvitation(token) {
  try {
    await ElMessageBox.confirm("Delete this invitation?", "Confirm", {
      type: "warning",
    });

    await invitationAPI.delete(token);
    ElMessage.success("Invitation deleted");
    await loadInvitations();
  } catch (err) {
    if (err !== "cancel") {
      console.error("Failed to delete invitation:", err);
      ElMessage.error("Failed to delete invitation");
    }
  }
}

// Watch tab changes to load data
watch(activeTab, (newTab) => {
  if (newTab === "members" && members.value.length === 0) {
    loadMembers();
  } else if (newTab === "invitations" && invitations.value.length === 0) {
    loadInvitations();
  }
});

onMounted(() => {
  loadOrgProfile();
  // Load members by default
  loadMembers();
});
</script>
