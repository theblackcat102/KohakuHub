<!-- src/kohaku-hub-ui/src/pages/index.vue -->
<template>
  <div>
    <!-- Hero Section -->
    <div class="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
      <div class="container-main py-20 text-center">
        <h1 class="text-5xl font-bold mb-4">
          Welcome to KohakuHub
        </h1>
        <p class="text-xl mb-8">
          Self-hosted HuggingFace Hub alternative for your AI models and datasets
        </p>
        <div class="flex gap-4 justify-center">
          <el-button size="large" type="primary" @click="$router.push('/models')">
            Browse Models
          </el-button>
          <el-button size="large" @click="$router.push('/register')">
            Get Started
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- Stats -->
    <div class="container-main py-12">
      <div class="grid grid-cols-3 gap-8 text-center">
        <div class="card">
          <div class="text-4xl font-bold text-blue-500 mb-2">{{ stats.models }}</div>
          <div class="text-gray-600">Models</div>
        </div>
        <div class="card">
          <div class="text-4xl font-bold text-green-500 mb-2">{{ stats.datasets }}</div>
          <div class="text-gray-600">Datasets</div>
        </div>
        <div class="card">
          <div class="text-4xl font-bold text-purple-500 mb-2">{{ stats.spaces }}</div>
          <div class="text-gray-600">Spaces</div>
        </div>
      </div>
    </div>
    
    <!-- Recent Repos -->
    <div class="container-main py-12">
      <h2 class="text-3xl font-bold mb-6">Recently Updated</h2>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Models" name="models">
          <RepoList :repos="recentModels" type="model" />
        </el-tab-pane>
        <el-tab-pane label="Datasets" name="datasets">
          <RepoList :repos="recentDatasets" type="dataset" />
        </el-tab-pane>
        <el-tab-pane label="Spaces" name="spaces">
          <RepoList :repos="recentSpaces" type="space" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { repoAPI } from '@/utils/api'
import RepoList from '@/components/repo/RepoList.vue'

const activeTab = ref('models')
const stats = ref({ models: 0, datasets: 0, spaces: 0 })
const recentModels = ref([])
const recentDatasets = ref([])
const recentSpaces = ref([])

async function loadStats() {
  try {
    const [models, datasets, spaces] = await Promise.all([
      repoAPI.listRepos('model', { limit: 50 }),
      repoAPI.listRepos('dataset', { limit: 50 }),
      repoAPI.listRepos('space', { limit: 50 })
    ])
    
    stats.value = {
      models: models.data.length,
      datasets: datasets.data.length,
      spaces: spaces.data.length
    }
    
    recentModels.value = models.data.slice(0, 10)
    recentDatasets.value = datasets.data.slice(0, 10)
    recentSpaces.value = spaces.data.slice(0, 10)
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

onMounted(() => {
  loadStats()
})
</script>