<!-- src/pages/[username]/index.vue -->
<template>
  <div class="container-main">
    <!-- User Not Found -->
    <div v-if="userNotFound" class="text-center py-20">
      <div
        class="i-carbon-user-avatar-filled text-8xl text-gray-300 dark:text-gray-600 mb-6 inline-block"
      />
      <h1 class="text-4xl font-bold mb-4">User Not Found</h1>
      <p class="text-xl text-gray-600 dark:text-gray-400 mb-8">
        The user "<span class="font-mono text-blue-600 dark:text-blue-400">{{
          username
        }}</span
        >" does not exist.
      </p>
      <el-button type="primary" @click="$router.push('/')">
        <div class="i-carbon-home mr-2" />
        Go to Homepage
      </el-button>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
      <!-- Sidebar -->
      <aside class="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <!-- Avatar -->
            <img
              v-if="hasAvatar"
              :src="`/api/users/${username}/avatar?t=${Date.now()}`"
              :alt="`${username} avatar`"
              class="w-20 h-20 rounded-full object-cover"
              @error="hasAvatar = false"
            />
            <div v-else class="i-carbon-user-avatar text-5xl text-gray-400" />

            <div>
              <h2 class="text-xl font-bold">{{ username }}</h2>
              <p class="text-sm text-gray-600 dark:text-gray-400">
                {{ profileInfo?.full_name || "User" }}
              </p>
            </div>
          </div>

          <div v-if="profileInfo" class="space-y-3 text-sm">
            <!-- Bio -->
            <p
              v-if="profileInfo.bio"
              class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap"
            >
              {{ profileInfo.bio }}
            </p>

            <!-- Links Section (Website + Social Media) -->
            <div
              v-if="profileInfo.website || profileInfo.social_media"
              class="flex gap-3"
            >
              <!-- Icons Column (10% width) -->
              <div class="flex flex-col gap-2 w-10% min-w-8">
                <!-- Website Icon -->
                <div
                  v-if="profileInfo.website"
                  class="flex items-center justify-center h-6"
                >
                  <div
                    class="i-carbon-link w-4 h-4 text-gray-600 dark:text-gray-400"
                  />
                </div>

                <!-- Social Media Icons -->
                <div
                  v-if="profileInfo.social_media?.twitter_x"
                  class="flex items-center justify-center h-6"
                >
                  <div
                    class="i-carbon-logo-x w-4 h-4 text-gray-600 dark:text-gray-400"
                  />
                </div>
                <div
                  v-if="profileInfo.social_media?.threads"
                  class="flex items-center justify-center h-6"
                >
                  <div
                    class="i-carbon-logo-instagram w-4 h-4 text-gray-600 dark:text-gray-400"
                  />
                </div>
                <div
                  v-if="profileInfo.social_media?.github"
                  class="flex items-center justify-center h-6"
                >
                  <div
                    class="i-carbon-logo-github w-4 h-4 text-gray-600 dark:text-gray-400"
                  />
                </div>
                <div
                  v-if="profileInfo.social_media?.huggingface"
                  class="flex items-center justify-center h-6"
                >
                  <span class="text-base">🤗</span>
                </div>
              </div>

              <!-- Links Column (90% width) -->
              <div class="flex flex-col gap-2 flex-1">
                <!-- Website Link -->
                <a
                  v-if="profileInfo.website"
                  :href="profileInfo.website"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center h-6 text-sm text-blue-600 dark:text-blue-400 hover:underline transition-colors truncate"
                  title="Website"
                >
                  {{ profileInfo.website.replace(/^https?:\/\//, "") }}
                </a>

                <!-- Social Media Links -->
                <a
                  v-if="profileInfo.social_media?.twitter_x"
                  :href="`https://twitter.com/${profileInfo.social_media.twitter_x}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate"
                  title="Twitter/X"
                >
                  @{{ profileInfo.social_media.twitter_x }}
                </a>

                <a
                  v-if="profileInfo.social_media?.threads"
                  :href="`https://www.threads.net/@${profileInfo.social_media.threads}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors truncate"
                  title="Threads"
                >
                  @{{ profileInfo.social_media.threads }}
                </a>

                <a
                  v-if="profileInfo.social_media?.github"
                  :href="`https://github.com/${profileInfo.social_media.github}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors truncate"
                  title="GitHub"
                >
                  {{ profileInfo.social_media.github }}
                </a>

                <a
                  v-if="profileInfo.social_media?.huggingface"
                  :href="`https://huggingface.co/${profileInfo.social_media.huggingface}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-yellow-600 dark:hover:text-yellow-400 transition-colors truncate"
                  title="HuggingFace"
                >
                  {{ profileInfo.social_media.huggingface }}
                </a>
              </div>
            </div>

            <!-- Joined Date -->
            <div
              class="flex items-center gap-2 text-gray-600 dark:text-gray-400 pt-2 border-t"
            >
              <div class="i-carbon-calendar" />
              Joined {{ formatDate(profileInfo.created_at) }}
            </div>
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

          <!-- View Details Button (only for users with write permission) -->
          <div v-if="quotaInfo.can_see_private" class="mt-4">
            <el-button
              size="small"
              @click="$router.push(`/${username}/storage`)"
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
              :to="`/${username}`"
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
              :to="`/${username}/models`"
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
              :to="`/${username}/datasets`"
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
              :to="`/${username}/spaces`"
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
        <!-- Sort Dropdown (applies to all sections) -->
        <div class="card">
          <el-select
            v-model="sortBy"
            placeholder="Sort by"
            class="w-full sm:w-50"
          >
            <el-option label="Recently Updated" value="recent" />
            <el-option label="Most Downloads" value="downloads" />
            <el-option label="Most Likes" value="likes" />
          </el-select>
        </div>

        <!-- User Card (from Username/Username space repo if exists) -->
        <section v-if="userCard" class="card">
          <div class="markdown-body">
            <MarkdownViewer :content="userCard" />
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
            <RouterLink :to="`/${username}/models`" class="block mt-4">
              <el-button v-if="hasMoreRepos('model')" class="w-full">
                Show all {{ getCount("model") }} models →
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
            <RouterLink :to="`/${username}/datasets`" class="block mt-4">
              <el-button v-if="hasMoreRepos('dataset')" class="w-full">
                Show all {{ getCount("dataset") }} datasets →
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
            <RouterLink :to="`/${username}/spaces`" class="block mt-4">
              <el-button v-if="hasMoreRepos('space')" class="w-full">
                Show all {{ getCount("space") }} spaces →
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
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import SocialLinks from "@/components/profile/SocialLinks.vue";
import axios from "axios";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

const route = useRoute();
const router = useRouter();
const username = computed(() => route.params.username);

const userInfo = ref(null);
const profileInfo = ref(null);
const repos = ref({ models: [], datasets: [], spaces: [] });
const userCard = ref("");
const userNotFound = ref(false);
const quotaInfo = ref(null);
const hasAvatar = ref(true); // Assume avatar exists, will be set to false on error
const sortBy = ref("recent"); // Sort option

const MAX_DISPLAYED = 6; // 2 per row × 3 rows

// Helper to convert singular type to plural key
function getPluralKey(type) {
  return type + "s";
}

function getCount(type) {
  return repos.value[getPluralKey(type)]?.length || 0;
}

function displayedRepos(type) {
  return (repos.value[getPluralKey(type)] || []).slice(0, MAX_DISPLAYED);
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

async function checkIfOrganization() {
  try {
    // Check if this name is an organization
    await orgAPI.get(username.value);
    // If successful, it's an organization - redirect
    router.replace(`/organizations/${username.value}`);
    return true;
  } catch (err) {
    // Not an organization, continue as user
    return false;
  }
}

async function loadUserData() {
  try {
    // Get user overview which returns all repos and validates user exists
    const response = await repoAPI.getUserOverview(
      username.value,
      sortBy.value,
    );
    repos.value = response.data;
    return true;
  } catch (err) {
    // Check if it's a 404 error
    if (err.response?.status === 404) {
      userNotFound.value = true;
      return false;
    }
    // For other errors, show empty repos
    console.error("Failed to load user data:", err);
    return true;
  }
}

// Watch sortBy changes and reload
watch(sortBy, () => {
  loadUserData();
});

async function loadUserCard() {
  try {
    // Try to fetch README from Username/Username space repo
    const url = `/spaces/${username.value}/${username.value}/resolve/main/README.md`;
    const response = await axios.get(url);
    userCard.value = response.data;
  } catch (err) {
    // No user card available - this is fine
    userCard.value = "";
  }
}

async function loadQuotaInfo() {
  try {
    const response = await axios.get(`/api/quota/${username.value}/public`, {
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
    const { data } = await settingsAPI.getUserProfile(username.value);
    profileInfo.value = data;
  } catch (err) {
    console.error("Failed to load profile info:", err);
    // Profile info is optional
    profileInfo.value = null;
  }
}

onMounted(async () => {
  // Check if this is actually an organization
  const isOrg = await checkIfOrganization();
  if (isOrg) return; // Already redirected

  // Load user data (repos) - this also validates user exists
  const userExists = await loadUserData();
  if (!userExists) {
    // userNotFound already set to true in loadUserData
    return;
  }

  // Load user card, profile, and quota info
  loadUserCard();
  loadProfileInfo();
  loadQuotaInfo();
});
</script>
