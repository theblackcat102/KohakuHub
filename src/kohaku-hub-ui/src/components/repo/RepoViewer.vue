<!-- src/components/repo/RepoViewer.vue -->
<template>
  <div class="container-main">
    <el-breadcrumb separator="/" class="mb-6 text-gray-700 dark:text-gray-300">
      <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s` }">
        {{ repoTypeLabel }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${namespace}` }">
        {{ namespace }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ name }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="loading" class="text-center py-20">
      <el-icon class="is-loading" :size="40">
        <div class="i-carbon-loading" />
      </el-icon>
    </div>

    <div v-else-if="error" class="text-center py-20">
      <div class="i-carbon-warning text-6xl text-red-500 mb-4" />
      <h2 class="text-2xl font-bold mb-2">Repository Not Found</h2>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <el-button @click="$router.back()">Go Back</el-button>
    </div>

    <div v-else class="grid grid-cols-[1fr_300px] gap-6">
      <!-- Main Content -->
      <main class="min-w-0">
        <!-- Repo Header -->
        <div class="card mb-6">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-3">
              <div :class="getIconClass(repoType)" class="text-4xl" />
              <div>
                <h1 class="text-3xl font-bold">{{ repoInfo?.id }}</h1>
                <div class="flex items-center gap-2 mt-1">
                  <RouterLink
                    :to="`/${namespace}`"
                    class="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {{ namespace }}
                  </RouterLink>
                  <span class="text-gray-400 dark:text-gray-500">/</span>
                  <span class="text-gray-700 dark:text-gray-300">{{
                    name
                  }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <el-tag v-if="repoInfo?.private" type="warning">
                <div class="i-carbon-locked inline-block mr-1" />
                Private
              </el-tag>
              <el-tag v-else type="success">
                <div class="i-carbon-unlocked inline-block mr-1" />
                Public
              </el-tag>
            </div>
          </div>

          <!-- Stats -->
          <div
            class="flex items-center gap-6 text-sm text-gray-600 dark:text-gray-400"
          >
            <div class="flex items-center gap-1">
              <div class="i-carbon-download" />
              <span>{{ repoInfo?.downloads || 0 }} downloads</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="i-carbon-favorite" />
              <span>{{ repoInfo?.likes || 0 }} likes</span>
            </div>
            <div class="flex items-center gap-1">
              <div class="i-carbon-calendar" />
              <span>Updated {{ formatDate(repoInfo?.lastModified) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 mt-4">
            <el-button type="primary" @click="showCloneDialog = true">
              <div class="i-carbon-download inline-block mr-1" />
              Clone
            </el-button>
            <el-button @click="downloadRepo">
              <div class="i-carbon-document-download inline-block mr-1" />
              Download
            </el-button>
            <el-button v-if="isOwner" @click="navigateToSettings">
              <div class="i-carbon-settings inline-block mr-1" />
              Settings
            </el-button>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="mb-6">
          <div class="flex gap-1 border-b border-gray-200 dark:border-gray-700">
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'card'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('card')"
            >
              {{
                repoType === "model"
                  ? "Model Card"
                  : repoType === "dataset"
                    ? "Dataset Card"
                    : "App"
              }}
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'files'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('files')"
            >
              Files
            </button>
            <button
              :class="[
                'px-4 py-2 font-medium transition-colors',
                activeTab === 'commits'
                  ? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
              ]"
              @click="navigateToTab('commits')"
            >
              Commits
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div v-if="activeTab === 'card'" class="card overflow-hidden">
          <div class="max-w-full overflow-x-auto">
            <div v-if="readmeContent">
              <MarkdownViewer
                :content="readmeContent"
                :repo-type="repoType"
                :namespace="namespace"
                :name="name"
                :branch="currentBranch"
              />
            </div>
            <div
              v-else
              class="text-center py-12 text-gray-500 dark:text-gray-400"
            >
              <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
              <p>No README.md found</p>
              <el-button
                v-if="isOwner"
                class="mt-4"
                type="primary"
                @click="createReadme"
              >
                Create README.md
              </el-button>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'files'" class="card">
          <div class="mb-4 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <el-select
                v-model="currentBranch"
                size="small"
                style="width: 150px"
                @change="handleBranchChange"
              >
                <el-option label="main" value="main" />
              </el-select>
              <span class="text-sm text-gray-600 dark:text-gray-400">
                {{ fileTree.length }}
                {{ fileTree.length === 1 ? "file" : "files" }}
              </span>
            </div>

            <div class="flex items-center gap-2">
              <el-button
                v-if="isOwner"
                size="small"
                type="primary"
                @click="navigateToUpload"
              >
                <div class="i-carbon-cloud-upload inline-block mr-1" />
                Upload Files
              </el-button>
              <el-input
                v-model="fileSearchQuery"
                placeholder="Search files..."
                size="small"
                style="width: 200px"
                clearable
              >
                <template #prefix>
                  <div class="i-carbon-search" />
                </template>
              </el-input>
            </div>
          </div>

          <!-- Breadcrumb for current path -->
          <div v-if="currentPath" class="mb-3 text-sm">
            <el-breadcrumb
              separator="/"
              class="text-gray-700 dark:text-gray-300"
            >
              <el-breadcrumb-item>
                <RouterLink
                  :to="`/${repoType}s/${namespace}/${name}/tree/${currentBranch}`"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  root
                </RouterLink>
              </el-breadcrumb-item>
              <el-breadcrumb-item
                v-for="(segment, idx) in pathSegments"
                :key="idx"
              >
                <RouterLink
                  :to="`/${repoType}s/${namespace}/${name}/tree/${currentBranch}/${pathSegments.slice(0, idx + 1).join('/')}`"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {{ segment }}
                </RouterLink>
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <!-- File List -->
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="file in filteredFiles"
              :key="file.path"
              class="py-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 cursor-pointer transition-colors"
              @click="handleFileClick(file)"
            >
              <div
                :class="
                  file.type === 'directory'
                    ? 'i-carbon-folder text-blue-500'
                    : 'i-carbon-document text-gray-500 dark:text-gray-400'
                "
                class="text-xl flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <div class="font-medium truncate">
                  {{ getFileName(file.path) }}
                </div>
              </div>
              <div class="text-sm text-gray-500 dark:text-gray-400">
                {{ formatSize(file.size) }}
              </div>
            </div>

            <div
              v-if="filteredFiles.length === 0"
              class="py-12 text-center text-gray-500 dark:text-gray-400"
            >
              <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
              <p>No files found</p>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'commits'" class="card">
          <div class="text-center py-12 text-gray-500 dark:text-gray-400">
            <div class="i-carbon-branch text-6xl mb-4 inline-block" />
            <p>Commit history coming soon</p>
          </div>
        </div>
      </main>

      <!-- Sidebar -->
      <aside class="space-y-4">
        <!-- Owner Info -->
        <div class="card">
          <h3 class="font-semibold mb-3">Owner</h3>
          <RouterLink
            :to="`/${namespace}`"
            class="flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-700 p-2 rounded transition-colors"
          >
            <div
              class="i-carbon-user-avatar text-3xl text-gray-400 dark:text-gray-500"
            />
            <span class="font-medium">{{ namespace }}</span>
          </RouterLink>
        </div>

        <!-- Tags -->
        <div v-if="repoInfo?.tags && repoInfo.tags.length" class="card">
          <h3 class="font-semibold mb-3">Tags</h3>
          <div class="flex flex-wrap gap-2">
            <el-tag v-for="tag in repoInfo.tags" :key="tag" size="small">
              {{ tag }}
            </el-tag>
          </div>
        </div>

        <!-- Metadata -->
        <div class="card">
          <h3 class="font-semibold mb-3">Metadata</h3>
          <div class="space-y-2 text-sm">
            <div>
              <span class="text-gray-600 dark:text-gray-400">Type:</span>
              <span class="ml-2 font-medium">{{ repoTypeLabel }}</span>
            </div>
            <div>
              <span class="text-gray-600 dark:text-gray-400">Created:</span>
              <span class="ml-2">{{ formatDate(repoInfo?.createdAt) }}</span>
            </div>
            <div v-if="repoInfo?.sha">
              <span class="text-gray-600 dark:text-gray-400">Commit:</span>
              <span class="ml-2 font-mono text-xs">{{
                repoInfo.sha.slice(0, 7)
              }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- Clone Dialog -->
    <el-dialog v-model="showCloneDialog" title="Clone Repository" width="600px">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Clone with HTTPS</label>
          <el-input :value="cloneUrl" readonly class="font-mono text-sm">
            <template #append>
              <el-button @click="copyCloneUrl">
                <div class="i-carbon-copy" />
              </el-button>
            </template>
          </el-input>
        </div>

        <div class="bg-gray-50 dark:bg-gray-900 p-4 rounded text-sm">
          <p class="mb-2 font-medium">Usage:</p>
          <pre class="text-xs overflow-x-auto">git clone {{ cloneUrl }}</pre>
          <p class="mt-3 text-gray-600 dark:text-gray-400">
            Or use
            <code class="bg-white dark:bg-gray-800 px-1 py-0.5 rounded"
              >huggingface-cli</code
            >:
          </p>
          <pre class="text-xs overflow-x-auto mt-1">
huggingface-cli download {{ repoInfo?.id }}</pre
          >
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { repoAPI } from "@/utils/api";
import { useAuthStore } from "@/stores/auth";
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

/**
 * @typedef {Object} Props
 * @property {string} repoType - Repository type (model/dataset/space)
 * @property {string} namespace - Repository namespace
 * @property {string} name - Repository name
 * @property {string} [branch] - Current branch
 * @property {string} [currentPath] - Current folder path
 * @property {string} [tab] - Active tab (card/files/commits)
 */
const props = defineProps({
  repoType: { type: String, required: true },
  namespace: { type: String, required: true },
  name: { type: String, required: true },
  branch: { type: String, default: "main" },
  currentPath: { type: String, default: "" },
  tab: { type: String, default: "card" },
});

const router = useRouter();
const authStore = useAuthStore();

// State
const loading = ref(true);
const error = ref(null);
const repoInfo = ref(null);
const currentBranch = ref(props.branch);
const fileTree = ref([]);
const readmeContent = ref("");
const showCloneDialog = ref(false);
const fileSearchQuery = ref("");

// Computed
const activeTab = computed(() => props.tab);

const repoTypeLabel = computed(() => {
  const labels = { model: "Models", dataset: "Datasets", space: "Spaces" };
  return labels[props.repoType] || "Models";
});

const isOwner = computed(() => {
  return authStore.username === props.namespace;
});

const cloneUrl = computed(() => {
  const baseUrl = window.location.origin;
  return `${baseUrl}/${repoInfo.value?.id}.git`;
});

const pathSegments = computed(() => {
  return props.currentPath ? props.currentPath.split("/").filter(Boolean) : [];
});

const filteredFiles = computed(() => {
  if (!fileSearchQuery.value) return fileTree.value;

  const query = fileSearchQuery.value.toLowerCase();
  return fileTree.value.filter((file) =>
    getFileName(file.path).toLowerCase().includes(query),
  );
});

// Methods
function getIconClass(type) {
  const icons = {
    model: "i-carbon-model text-blue-500",
    dataset: "i-carbon-data-table text-green-500",
    space: "i-carbon-application text-purple-500",
  };
  return icons[type] || icons.model;
}

function formatDate(date) {
  return date ? dayjs(date).fromNow() : "Unknown";
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return "-";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}

function getFileName(path) {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

function navigateToTab(tab) {
  if (tab === "files") {
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}`,
    );
  } else if (tab === "commits") {
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/commits/${currentBranch.value}`,
    );
  } else {
    router.push(`/${props.repoType}s/${props.namespace}/${props.name}`);
  }
}

function navigateToSettings() {
  router.push(`/${props.repoType}s/${props.namespace}/${props.name}/settings`);
}

function navigateToUpload() {
  router.push(
    `/${props.repoType}s/${props.namespace}/${props.name}/upload/${currentBranch.value}`,
  );
}

function handleBranchChange() {
  if (activeTab.value === "files") {
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}`,
    );
  }
}

async function loadRepoInfo() {
  loading.value = true;
  error.value = null;

  try {
    const { data } = await repoAPI.getInfo(
      props.repoType,
      props.namespace,
      props.name,
    );
    repoInfo.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || "Failed to load repository";
    console.error("Failed to load repo info:", err);
  } finally {
    loading.value = false;
  }
}

async function loadFileTree() {
  try {
    const { data } = await repoAPI.listTree(
      props.repoType,
      props.namespace,
      props.name,
      currentBranch.value,
      props.currentPath ? `/${props.currentPath}` : "",
      { recursive: false },
    );

    fileTree.value = data.sort((a, b) => {
      if (a.type === "directory" && b.type !== "directory") return -1;
      if (a.type !== "directory" && b.type === "directory") return 1;
      return a.path.localeCompare(b.path);
    });
  } catch (err) {
    console.error("Failed to load file tree:", err);
    fileTree.value = [];
  }
}

async function loadReadme() {
  try {
    const readmeFile = fileTree.value.find(
      (f) => f.type === "file" && f.path.toLowerCase().endsWith("readme.md"),
    );

    if (!readmeFile) {
      readmeContent.value = "";
      return;
    }

    const downloadUrl = `/${props.repoType}s/${props.namespace}/${props.name}/resolve/${currentBranch.value}/${readmeFile.path}`;
    const response = await fetch(downloadUrl);

    if (response.ok) {
      readmeContent.value = await response.text();
    }
  } catch (err) {
    console.error("Failed to load README:", err);
    readmeContent.value = "";
  }
}

function handleFileClick(file) {
  if (file.type === "directory") {
    // Navigate to folder using tree route
    const newPath = props.currentPath
      ? `${props.currentPath}/${file.path}`
      : file.path;
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/tree/${currentBranch.value}/${newPath}`,
    );
  } else {
    // Navigate to file viewer using blob route
    const fullPath = props.currentPath
      ? `${props.currentPath}/${file.path}`
      : file.path;
    router.push(
      `/${props.repoType}s/${props.namespace}/${props.name}/blob/${currentBranch.value}/${fullPath}`,
    );
  }
}

function downloadRepo() {
  ElMessage.info("Download functionality coming soon");
}

function createReadme() {
  ElMessage.info("README creation coming soon");
}

function copyCloneUrl() {
  navigator.clipboard.writeText(cloneUrl.value);
  ElMessage.success("Clone URL copied to clipboard");
}

// Watchers
watch(
  () => props.currentPath,
  () => {
    if (activeTab.value === "files") {
      loadFileTree();
    }
  },
);

watch(
  () => props.branch,
  (newBranch) => {
    currentBranch.value = newBranch;
    if (activeTab.value === "files") {
      loadFileTree();
    }
  },
);

watch(
  () => props.tab,
  async (newTab) => {
    if (newTab === "files" && fileTree.value.length === 0) {
      await loadFileTree();
    } else if (newTab === "card" && !readmeContent.value) {
      if (fileTree.value.length === 0) {
        await loadFileTree();
      }
      await loadReadme();
    }
  },
);

watch(
  fileTree,
  () => {
    if (activeTab.value === "card" && !readmeContent.value) {
      loadReadme();
    }
  },
  { immediate: false },
);

// Lifecycle
onMounted(async () => {
  await loadRepoInfo();

  if (activeTab.value === "files") {
    await loadFileTree();
  } else if (activeTab.value === "card") {
    await loadFileTree();
    await loadReadme();
  }
});
</script>
