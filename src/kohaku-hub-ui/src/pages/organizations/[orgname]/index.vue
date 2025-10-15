<!-- src/pages/organizations/[orgname]/index.vue -->
<template>
  <div class="container-main">
    <!-- Header with Settings Button -->
    <div v-if="isAdmin" class="flex items-center justify-end mb-4">
      <el-button
        type="primary"
        size="small"
        @click="$router.push(`/organizations/${orgname}/settings`)"
      >
        <div class="i-carbon-settings mr-1" />
        Organization Settings
      </el-button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
      <!-- Sidebar with members -->
      <aside class="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <!-- Avatar -->
            <img
              v-if="hasAvatar"
              :src="`/api/organizations/${orgname}/avatar?t=${Date.now()}`"
              :alt="`${orgname} avatar`"
              class="w-20 h-20 rounded-full object-cover"
              @error="hasAvatar = false"
            />
            <div v-else class="i-carbon-group text-5xl text-gray-400" />

            <div>
              <h2 class="text-xl font-bold">{{ orgname }}</h2>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Organization
              </p>
            </div>
          </div>

          <div v-if="profileInfo" class="space-y-3 text-sm">
            <!-- Description -->
            <p
              v-if="profileInfo.description"
              class="text-gray-700 dark:text-gray-300"
            >
              {{ profileInfo.description }}
            </p>

            <!-- Bio -->
            <p
              v-if="profileInfo.bio"
              class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap"
            >
              {{ profileInfo.bio }}
            </p>

            <!-- Website -->
            <a
              v-if="profileInfo.website"
              :href="profileInfo.website"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:underline"
            >
              <div class="i-carbon-link" />
              {{ profileInfo.website.replace(/^https?:\/\//, "") }}
            </a>

            <!-- Social Media -->
            <SocialLinks
              v-if="profileInfo.social_media"
              :social-media="profileInfo.social_media"
            />

            <!-- Created Date -->
            <div
              class="flex items-center gap-2 text-gray-600 dark:text-gray-400 pt-2 border-t"
            >
              <div class="i-carbon-calendar" />
              Created {{ formatDate(profileInfo.created_at) }}
            </div>

            <!-- Member Count -->
            <div
              class="flex items-center gap-2 text-gray-600 dark:text-gray-400"
            >
              <div class="i-carbon-user-multiple" />
              {{ profileInfo.member_count || members.length }} member{{
                (profileInfo.member_count || members.length) !== 1 ? "s" : ""
              }}
            </div>
          </div>
        </div>

        <!-- Members List -->
        <div class="card">
          <h3 class="font-semibold mb-3 flex items-center gap-2">
            <div class="i-carbon-user-multiple" />
            Members
            <span class="text-sm text-gray-500"
              >({{ members.length || 0 }})</span
            >
          </h3>
          <div v-if="members.length > 0" class="space-y-2">
            <div
              v-for="member in members"
              :key="member.user"
              class="flex items-center gap-2 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              @click="goToUser(member.user)"
            >
              <!-- Member Avatar -->
              <img
                :src="`/api/users/${member.user}/avatar?t=${Date.now()}`"
                :alt="`${member.user} avatar`"
                class="w-8 h-8 rounded-full object-cover border border-gray-300 dark:border-gray-600"
                @error="(e) => { e.target.style.display = 'none'; e.target.nextElementSibling.style.display = 'block'; }"
              />
              <div class="i-carbon-user-avatar text-2xl text-gray-400" style="display: none" />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">
                  {{ member.user }}
                </div>
                <div class="text-xs text-gray-500">
                  {{ member.role }}
                </div>
              </div>
            </div>
          </div>
          <div
            v-else
            class="text-center py-4 text-sm text-gray-500 dark:text-gray-400"
          >
            No members yet
          </div>
        </div>

        <!-- Storage Quota Card -->
        <div v-if="quotaInfo" class="card">
          <h3 class="font-semibold mb-3 flex items-center gap-2">
            <div class="i-carbon-data-base text-gray-500" />
            Storage Usage
          </h3>

          <!-- Public Storage -->
          <div class="mb-4">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >Public</span
              >
              <span class="text-sm font-mono">
                {{ formatBytes(quotaInfo.public_used_bytes) }}
                <span
                  v-if="quotaInfo.public_quota_bytes !== null"
                  class="text-gray-400"
                >
                  / {{ formatBytes(quotaInfo.public_quota_bytes) }}
                </span>
                <span v-else class="text-gray-400">/ Unlimited</span>
              </span>
            </div>
            <el-progress
              v-if="quotaInfo.public_quota_bytes !== null"
              :percentage="Math.min(100, quotaInfo.public_percentage_used || 0)"
              :status="getQuotaStatus(quotaInfo.public_percentage_used)"
              :show-text="false"
            />
            <div
              v-else
              class="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full"
            ></div>
          </div>

          <!-- Private Storage (only if user has permission) -->
          <div v-if="quotaInfo.can_see_private" class="mb-2">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >Private</span
              >
              <span class="text-sm font-mono">
                {{ formatBytes(quotaInfo.private_used_bytes) }}
                <span
                  v-if="quotaInfo.private_quota_bytes !== null"
                  class="text-gray-400"
                >
                  / {{ formatBytes(quotaInfo.private_quota_bytes) }}
                </span>
                <span v-else class="text-gray-400">/ Unlimited</span>
              </span>
            </div>
            <el-progress
              v-if="quotaInfo.private_quota_bytes !== null"
              :percentage="
                Math.min(100, quotaInfo.private_percentage_used || 0)
              "
              :status="getQuotaStatus(quotaInfo.private_percentage_used)"
              :show-text="false"
            />
            <div
              v-else
              class="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full"
            ></div>
          </div>

          <!-- Total -->
          <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
            <div class="flex justify-between items-center">
              <span class="text-sm font-semibold">Total</span>
              <span class="text-sm font-mono font-semibold">
                {{ formatBytes(quotaInfo.total_used_bytes) }}
              </span>
            </div>
          </div>

          <!-- View Details Button (only for members with write permission) -->
          <div v-if="quotaInfo.can_see_private" class="mt-4">
            <el-button
              size="small"
              @click="$router.push(`/organizations/${orgname}/storage`)"
              class="w-full"
            >
              <div class="i-carbon-chart-bar inline-block mr-1" />
              View Details
            </el-button>
          </div>
        </div>

        <!-- Stats Summary / Tab Navigation -->
        <div class="card">
          <h3 class="font-semibold mb-3">Repositories</h3>
          <div class="space-y-1">
            <RouterLink
              :to="`/organizations/${orgname}`"
              :class="[
                'flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors block',
                'bg-gray-100 dark:bg-gray-700',
              ]"
            >
              <div class="flex items-center gap-2 text-sm">
                <div class="i-carbon-grid text-gray-500 dark:text-gray-400" />
                <span class="font-semibold">Overview</span>
              </div>
            </RouterLink>

            <RouterLink
              :to="`/organizations/${orgname}/models`"
              :class="[
                'flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors block',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
              ]"
            >
              <div class="flex items-center gap-2 text-sm">
                <div class="i-carbon-model text-blue-500" />
                <span>Models</span>
              </div>
              <span
                class="text-sm font-semibold text-gray-600 dark:text-gray-400"
              >
                {{ getCount("model") }}
              </span>
            </RouterLink>

            <RouterLink
              :to="`/organizations/${orgname}/datasets`"
              :class="[
                'flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors block',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
              ]"
            >
              <div class="flex items-center gap-2 text-sm">
                <div class="i-carbon-data-table text-green-500" />
                <span>Datasets</span>
              </div>
              <span
                class="text-sm font-semibold text-gray-600 dark:text-gray-400"
              >
                {{ getCount("dataset") }}
              </span>
            </RouterLink>

            <RouterLink
              :to="`/organizations/${orgname}/spaces`"
              :class="[
                'flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors block',
                'hover:bg-gray-100 dark:hover:bg-gray-700',
              ]"
            >
              <div class="flex items-center gap-2 text-sm">
                <div class="i-carbon-application text-purple-500" />
                <span>Spaces</span>
              </div>
              <span
                class="text-sm font-semibold text-gray-600 dark:text-gray-400"
              >
                {{ getCount("space") }}
              </span>
            </RouterLink>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="space-y-8">
        <!-- Organization Card (from OrgName/OrgName space repo card if exists) -->
        <section v-if="orgCard" class="card">
          <div class="markdown-body">
            <MarkdownViewer :content="orgCard" />
          </div>
        </section>

        <!-- Models Section -->
        <section class="mb-8">
          <div
            class="flex items-center justify-between mb-4 pb-3 border-b-2 border-blue-500"
          >
            <div class="flex items-center gap-2">
              <div class="i-carbon-model text-blue-500 text-xl md:text-2xl" />
              <h2 class="text-xl md:text-2xl font-bold">Models</h2>
            </div>
            <el-tag type="info" size="large">{{ getCount("model") }}</el-tag>
          </div>

          <div v-if="getCount('model') > 0" class="space-y-4">
            <!-- Grid of repos (2 per row, max 3 rows = 6 repos) -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div
                v-for="repo in displayedRepos('model')"
                :key="repo.id"
                class="card hover:shadow-md transition-shadow cursor-pointer"
                @click="goToRepo('model', repo)"
              >
                <div class="flex items-start gap-2 mb-2">
                  <div
                    class="i-carbon-model text-blue-500 text-xl flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0">
                    <h3
                      class="font-semibold text-blue-600 dark:text-blue-400 hover:underline truncate"
                    >
                      {{ repo.id }}
                    </h3>
                    <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      Updated {{ formatDate(repo.lastModified) }}
                    </div>
                  </div>
                </div>

                <div
                  v-if="repo.tags && repo.tags.length"
                  class="flex gap-1 mb-2 flex-wrap"
                >
                  <el-tag
                    v-for="tag in repo.tags.slice(0, 2)"
                    :key="tag"
                    size="small"
                    effect="plain"
                  >
                    {{ tag }}
                  </el-tag>
                </div>

                <div
                  class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400"
                >
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-download" />
                    {{ repo.downloads || 0 }}
                  </div>
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-favorite" />
                    {{ repo.likes || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Show More button -->
            <RouterLink :to="`/organizations/${orgname}/models`">
              <el-button v-if="hasMoreRepos('model')" class="w-full">
                Show all {{ getCount("model") }} models ->
              </el-button>
            </RouterLink>
          </div>

          <div
            v-else
            class="text-center py-12 text-gray-500 dark:text-gray-400"
          >
            <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
            <p>No models yet</p>
          </div>
        </section>

        <!-- Datasets Section -->
        <section class="mb-8">
          <div
            class="flex items-center justify-between mb-4 pb-3 border-b-2 border-green-500"
          >
            <div class="flex items-center gap-2">
              <div
                class="i-carbon-data-table text-green-500 text-xl md:text-2xl"
              />
              <h2 class="text-xl md:text-2xl font-bold">Datasets</h2>
            </div>
            <el-tag type="success" size="large">{{
              getCount("dataset")
            }}</el-tag>
          </div>

          <div v-if="getCount('dataset') > 0" class="space-y-4">
            <!-- Grid of repos (2 per row, max 3 rows = 6 repos) -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div
                v-for="repo in displayedRepos('dataset')"
                :key="repo.id"
                class="card hover:shadow-md transition-shadow cursor-pointer"
                @click="goToRepo('dataset', repo)"
              >
                <div class="flex items-start gap-2 mb-2">
                  <div
                    class="i-carbon-data-table text-green-500 text-xl flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0">
                    <h3
                      class="font-semibold text-green-600 dark:text-green-400 hover:underline truncate"
                    >
                      {{ repo.id }}
                    </h3>
                    <div class="text-xs text-gray-600 mt-1">
                      Updated {{ formatDate(repo.lastModified) }}
                    </div>
                  </div>
                </div>

                <div
                  v-if="repo.tags && repo.tags.length"
                  class="flex gap-1 mb-2 flex-wrap"
                >
                  <el-tag
                    v-for="tag in repo.tags.slice(0, 2)"
                    :key="tag"
                    size="small"
                    effect="plain"
                  >
                    {{ tag }}
                  </el-tag>
                </div>

                <div
                  class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400"
                >
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-download" />
                    {{ repo.downloads || 0 }}
                  </div>
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-favorite" />
                    {{ repo.likes || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Show More button -->
            <RouterLink :to="`/organizations/${orgname}/datasets`">
              <el-button v-if="hasMoreRepos('dataset')" class="w-full">
                Show all {{ getCount("dataset") }} datasets ->
              </el-button>
            </RouterLink>
          </div>

          <div
            v-else
            class="text-center py-12 text-gray-500 dark:text-gray-400"
          >
            <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
            <p>No datasets yet</p>
          </div>
        </section>

        <!-- Spaces Section -->
        <section>
          <div
            class="flex items-center justify-between mb-4 pb-3 border-b-2 border-purple-500"
          >
            <div class="flex items-center gap-2">
              <div
                class="i-carbon-application text-purple-500 text-xl md:text-2xl"
              />
              <h2 class="text-xl md:text-2xl font-bold">Spaces</h2>
            </div>
            <el-tag type="warning" size="large">{{ getCount("space") }}</el-tag>
          </div>

          <div v-if="getCount('space') > 0" class="space-y-4">
            <!-- Grid of repos (2 per row, max 3 rows = 6 repos) -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div
                v-for="repo in displayedRepos('space')"
                :key="repo.id"
                class="card hover:shadow-md transition-shadow cursor-pointer"
                @click="goToRepo('space', repo)"
              >
                <div class="flex items-start gap-2 mb-2">
                  <div
                    class="i-carbon-application text-purple-500 text-xl flex-shrink-0"
                  />
                  <div class="flex-1 min-w-0">
                    <h3
                      class="font-semibold text-purple-600 dark:text-purple-400 hover:underline truncate"
                    >
                      {{ repo.id }}
                    </h3>
                    <div class="text-xs text-gray-600 mt-1">
                      Updated {{ formatDate(repo.lastModified) }}
                    </div>
                  </div>
                </div>

                <div
                  v-if="repo.tags && repo.tags.length"
                  class="flex gap-1 mb-2 flex-wrap"
                >
                  <el-tag
                    v-for="tag in repo.tags.slice(0, 2)"
                    :key="tag"
                    size="small"
                    effect="plain"
                  >
                    {{ tag }}
                  </el-tag>
                </div>

                <div
                  class="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400"
                >
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-download" />
                    {{ repo.downloads || 0 }}
                  </div>
                  <div class="flex items-center gap-1">
                    <div class="i-carbon-favorite" />
                    {{ repo.likes || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Show More button -->
            <RouterLink :to="`/organizations/${orgname}/spaces`">
              <el-button v-if="hasMoreRepos('space')" class="w-full">
                Show all {{ getCount("space") }} spaces ->
              </el-button>
            </RouterLink>
          </div>

          <div
            v-else
            class="text-center py-12 text-gray-500 dark:text-gray-400"
          >
            <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
            <p>No spaces yet</p>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { repoAPI, orgAPI, settingsAPI } from "@/utils/api";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import SocialLinks from "@/components/profile/SocialLinks.vue";
import axios from "axios";

dayjs.extend(relativeTime);

const route = useRoute();
const router = useRouter();
const orgname = computed(() => route.params.orgname);

const orgInfo = ref(null);
const profileInfo = ref(null);
const members = ref([]);
const repos = ref({ model: [], dataset: [], space: [] });
const orgCard = ref("");
const quotaInfo = ref(null);
const userRole = ref(null);
const hasAvatar = ref(true); // Assume avatar exists, will be set to false on error

const MAX_DISPLAYED = 6; // 2 per row × 3 rows

const isAdmin = computed(() => {
  return userRole.value && ["admin", "super-admin"].includes(userRole.value);
});

function getCount(type) {
  return repos.value[type]?.length || 0;
}

function displayedRepos(type) {
  return (repos.value[type] || []).slice(0, MAX_DISPLAYED);
}

function hasMoreRepos(type) {
  return getCount(type) > MAX_DISPLAYED;
}

function formatDate(date) {
  return date ? dayjs(date).fromNow() : "never";
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "Unlimited";
  if (bytes === 0) return "0 B";
  const k = 1000;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getQuotaStatus(percentage) {
  if (percentage === null || percentage === undefined) return "";
  if (percentage >= 90) return "exception";
  if (percentage >= 75) return "warning";
  return "success";
}

function goToRepo(type, repo) {
  const [namespace, name] = repo.id.split("/");
  router.push(`/${type}s/${namespace}/${name}`);
}

function goToUser(username) {
  router.push(`/${username}`);
}

async function loadOrgInfo() {
  try {
    const { data } = await orgAPI.get(orgname.value);
    orgInfo.value = data;
  } catch (err) {
    console.error("Failed to load org info:", err);
  }
}

async function loadMembers() {
  try {
    const { data } = await orgAPI.listMembers(orgname.value);
    members.value = data.members || [];
  } catch (err) {
    console.error("Failed to load members:", err);
  }
}

async function loadRepos() {
  try {
    const [models, datasets, spaces] = await Promise.all([
      repoAPI.listRepos("model", { author: orgname.value }),
      repoAPI.listRepos("dataset", { author: orgname.value }),
      repoAPI.listRepos("space", { author: orgname.value }),
    ]);

    repos.value = {
      model: models.data,
      dataset: datasets.data,
      space: spaces.data,
    };
  } catch (err) {
    console.error("Failed to load repos:", err);
  }
}

async function loadOrgCard() {
  try {
    // Try to fetch README from OrgName/OrgName space repo
    const url = `/spaces/${orgname.value}/${orgname.value}/resolve/main/README.md`;
    const response = await axios.get(url);
    orgCard.value = response.data;
  } catch (err) {
    // No org card available - this is fine
    orgCard.value = "";
  }
}

async function loadQuotaInfo() {
  try {
    const response = await axios.get(`/api/quota/${orgname.value}/public`, {
      withCredentials: true,
    });
    quotaInfo.value = response.data;
  } catch (err) {
    console.error("Failed to load quota info:", err);
    // Don't show error to user - quota info is optional
    quotaInfo.value = null;
  }
}

async function loadProfileInfo() {
  try {
    const { data } = await settingsAPI.getOrgProfile(orgname.value);
    profileInfo.value = data;
  } catch (err) {
    console.error("Failed to load profile info:", err);
    // Profile info is optional
    profileInfo.value = null;
  }
}

async function checkUserRole() {
  try {
    const { data } = await settingsAPI.whoamiV2();
    const org = data.orgs?.find((o) => o.name === orgname.value);
    userRole.value = org?.roleInOrg || org?.role || null;
  } catch (err) {
    // Not logged in or error - user is not a member
    userRole.value = null;
  }
}

onMounted(() => {
  checkUserRole();
  loadOrgInfo();
  loadProfileInfo();
  loadMembers();
  loadRepos();
  loadOrgCard();
  loadQuotaInfo();
});
</script>
