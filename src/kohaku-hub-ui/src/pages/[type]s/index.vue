<!-- src/kohaku-hub-ui/src/pages/[type]s/index.vue -->
<template>
  <div class="container-main">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl md:text-3xl font-bold mb-2">{{ pageTitle }}</h1>
        <p class="text-sm md:text-base text-gray-600 dark:text-gray-400">{{ pageDescription }}</p>
      </div>

      <el-button
        v-if="isAuthenticated"
        type="primary"
        size="large"
        @click="showCreateDialog = true"
        class="w-full md:w-auto"
      >
        <div class="i-carbon-add inline-block mr-1" />
        New {{ repoTypeLabel }}
      </el-button>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <el-input
          v-model="searchQuery"
          :placeholder="`Search ${repoType}s...`"
          clearable
          class="flex-1"
        >
          <template #prefix>
            <div class="i-carbon-search" />
          </template>
        </el-input>

        <el-select v-model="sortBy" placeholder="Sort by" class="w-full sm:w-50">
          <el-option label="Recently Updated" value="updated" />
          <el-option label="Recently Created" value="created" />
          <el-option label="Most Downloads" value="downloads" />
          <el-option label="Most Likes" value="likes" />
        </el-select>
      </div>
    </div>

    <!-- Repository List -->
    <el-skeleton :loading="loading" :rows="5" animated>
      <RepoList :repos="filteredRepos" :type="repoType" />
    </el-skeleton>

    <!-- Create Repository Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="`Create New ${repoTypeLabel}`"
      width="500px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item :label="`${repoTypeLabel} Name`" prop="name">
          <el-input v-model="form.name" :placeholder="`my-${repoType}`" />
          <div class="text-xs text-gray-500 mt-1">
            Full name: {{ currentUser }}/{{ form.name || `${repoType}-name` }}
          </div>
        </el-form-item>

        <el-form-item label="Organization (Optional)" prop="organization">
          <el-select
            v-model="form.organization"
            placeholder="Select organization or leave empty"
            clearable
            class="w-full"
          >
            <el-option
              v-for="org in userOrgs"
              :key="org.name"
              :label="org.name"
              :value="org.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.private">
            Make this {{ repoType }} private
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          Create {{ repoTypeLabel }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { repoAPI, orgAPI } from "@/utils/api";
import { useAuthStore } from "@/stores/auth";
import RepoList from "@/components/repo/RepoList.vue";
import { ElMessage } from "element-plus";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { isAuthenticated, username: currentUser } = storeToRefs(authStore);

// Determine repo type from route path
const repoType = computed(() => {
  const path = route.path;
  if (path.startsWith("/models")) return "model";
  if (path.startsWith("/datasets")) return "dataset";
  if (path.startsWith("/spaces")) return "space";
  return "model";
});

const repoTypeLabel = computed(() => {
  const labels = { model: "Model", dataset: "Dataset", space: "Space" };
  return labels[repoType.value] || "Model";
});

const pageTitle = computed(() => {
  const titles = { model: "Models", dataset: "Datasets", space: "Spaces" };
  return titles[repoType.value] || "Models";
});

const pageDescription = computed(() => {
  const descriptions = {
    model: "Discover and share machine learning models",
    dataset: "Discover and share datasets for machine learning",
    space: "Discover ML demos and applications",
  };
  return descriptions[repoType.value] || "";
});

const loading = ref(true);
const repos = ref([]);
const searchQuery = ref("");
const sortBy = ref("updated");
const showCreateDialog = ref(false);
const creating = ref(false);
const userOrgs = ref([]);
const formRef = ref(null);

const form = reactive({
  name: "",
  organization: "",
  private: false,
});

const rules = {
  name: [
    {
      required: true,
      message: `Please enter ${repoType.value} name`,
      trigger: "blur",
    },
    {
      pattern: /^[a-zA-Z0-9_-]+$/,
      message: "Only letters, numbers, hyphens and underscores allowed",
      trigger: "blur",
    },
  ],
};

const filteredRepos = computed(() => {
  let result = [...repos.value];

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (repo) =>
        repo.id.toLowerCase().includes(query) ||
        repo.author.toLowerCase().includes(query),
    );
  }

  result.sort((a, b) => {
    switch (sortBy.value) {
      case "updated":
        return new Date(b.lastModified || 0) - new Date(a.lastModified || 0);
      case "created":
        return new Date(b.createdAt || 0) - new Date(a.createdAt || 0);
      case "downloads":
        return (b.downloads || 0) - (a.downloads || 0);
      case "likes":
        return (b.likes || 0) - (a.likes || 0);
      default:
        return 0;
    }
  });

  return result;
});

async function loadRepos() {
  loading.value = true;
  try {
    const { data } = await repoAPI.listRepos(repoType.value, { limit: 100 });
    repos.value = data;
  } catch (err) {
    console.error(`Failed to load ${repoType.value}s:`, err);
    ElMessage.error(`Failed to load ${repoType.value}s`);
  } finally {
    loading.value = false;
  }
}

async function loadUserOrgs() {
  if (!currentUser.value) return;

  try {
    const { data } = await orgAPI.getUserOrgs(currentUser.value);
    userOrgs.value = data.organizations || [];
  } catch (err) {
    console.error("Failed to load organizations:", err);
  }
}

async function handleCreate() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    creating.value = true;
    try {
      const { data } = await repoAPI.create({
        type: repoType.value,
        name: form.name,
        organization: form.organization || null,
        private: form.private,
      });

      ElMessage.success(`${repoTypeLabel.value} created successfully`);
      showCreateDialog.value = false;

      const repoId =
        data.repo_id ||
        `${form.organization || currentUser.value}/${form.name}`;
      router.push(`/${repoType.value}s/${repoId}`);
    } catch (err) {
      ElMessage.error(
        err.response?.data?.detail || `Failed to create ${repoType.value}`,
      );
    } finally {
      creating.value = false;
    }
  });
}

watch(showCreateDialog, (val) => {
  if (val) {
    loadUserOrgs();
  } else {
    form.name = "";
    form.organization = "";
    form.private = false;
  }
});

// Reload repos when route changes
watch(
  () => route.path,
  () => {
    loadRepos();
  },
  { immediate: true },
);

onMounted(() => {
  loadRepos();
});
</script>
