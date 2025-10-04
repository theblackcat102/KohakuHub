<!-- src/pages/[username]/index.vue -->
<template>
  <div class="container-main">
    <div class="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
      <!-- Sidebar -->
      <aside class="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <div class="i-carbon-user-avatar text-5xl text-gray-400" />
            <div>
              <h2 class="text-xl font-bold">{{ username }}</h2>
              <p class="text-sm text-gray-600 dark:text-gray-400">User</p>
            </div>
          </div>

          <div class="space-y-2 text-sm">
            <div
              class="flex items-center gap-2 text-gray-600 dark:text-gray-400"
            >
              <div class="i-carbon-calendar" />
              Joined {{ formatDate(userInfo?.created_at) }}
            </div>
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
                'hover:bg-gray-50 dark:hover:bg-gray-700',
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
                'hover:bg-gray-50 dark:hover:bg-gray-700',
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
                'hover:bg-gray-50 dark:hover:bg-gray-700',
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
            <RouterLink :to="`/${username}/models`">
              <el-button v-if="hasMoreRepos('model')" text class="w-full">
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
            <RouterLink :to="`/${username}/datasets`">
              <el-button v-if="hasMoreRepos('dataset')" text class="w-full">
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
            <RouterLink :to="`/${username}/spaces`">
              <el-button v-if="hasMoreRepos('space')" text class="w-full">
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
import { repoAPI } from "@/utils/api";
import dayjs from "dayjs";

const route = useRoute();
const router = useRouter();
const username = computed(() => route.params.username);

const userInfo = ref(null);
const repos = ref({ model: [], dataset: [], space: [] });

const MAX_DISPLAYED = 6; // 2 per row × 3 rows

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
  return date ? dayjs(date).format("MMM YYYY") : "";
}

function goToRepo(type, repo) {
  const [namespace, name] = repo.id.split("/");
  router.push(`/${type}s/${namespace}/${name}`);
}

async function loadRepos() {
  try {
    const [models, datasets, spaces] = await Promise.all([
      repoAPI.listRepos("model", { author: username.value }),
      repoAPI.listRepos("dataset", { author: username.value }),
      repoAPI.listRepos("space", { author: username.value }),
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

onMounted(() => {
  loadRepos();
});
</script>
