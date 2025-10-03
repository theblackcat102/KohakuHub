<!-- src/kohaku-hub-ui/src/pages/[username]/index.vue -->
<template>
  <div class="container-main">
    <div class="grid grid-cols-[280px_1fr] gap-6">
      <!-- Sidebar -->
      <aside class="space-y-4">
        <div class="card">
          <div class="flex items-center gap-3 mb-4">
            <div class="i-carbon-user-avatar text-5xl text-gray-400" />
            <div>
              <h2 class="text-xl font-bold">{{ username }}</h2>
              <p class="text-sm text-gray-600">User</p>
            </div>
          </div>
          
          <div class="space-y-2 text-sm">
            <div class="flex items-center gap-2 text-gray-600">
              <div class="i-carbon-calendar" />
              Joined {{ formatDate(userInfo?.created_at) }}
            </div>
          </div>
        </div>
        
        <!-- Navigation -->
        <div class="card">
          <div class="space-y-1">
            <div
              v-for="item in navItems"
              :key="item.type"
              :class="[
                'px-3 py-2 rounded cursor-pointer flex items-center gap-2',
                activeType === item.type ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'
              ]"
              @click="activeType = item.type"
            >
              <div :class="item.icon" />
              <span>{{ item.label }}</span>
              <span class="ml-auto text-gray-500">{{ getCount(item.type) }}</span>
            </div>
          </div>
        </div>
      </aside>
      
      <!-- Main Content -->
      <main>
        <div class="mb-6">
          <h1 class="text-2xl font-bold mb-2">{{ activeLabel }}</h1>
          <p class="text-gray-600">{{ getCount(activeType) }} repositories</p>
        </div>
        
        <RepoList :repos="filteredRepos" :type="activeType" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { repoAPI } from '@/utils/api'
import RepoList from '@/components/repo/RepoList.vue'
import dayjs from 'dayjs'

const route = useRoute()
const username = computed(() => route.params.username)

const activeType = ref('model')
const userInfo = ref(null)
const repos = ref({ model: [], dataset: [], space: [] })

const navItems = [
  { type: 'model', label: 'Models', icon: 'i-carbon-model' },
  { type: 'dataset', label: 'Datasets', icon: 'i-carbon-data-table' },
  { type: 'space', label: 'Spaces', icon: 'i-carbon-application' }
]

const activeLabel = computed(() => {
  return navItems.find(item => item.type === activeType.value)?.label || 'Repositories'
})

const filteredRepos = computed(() => {
  return repos.value[activeType.value] || []
})

function getCount(type) {
  return repos.value[type]?.length || 0
}

function formatDate(date) {
  return date ? dayjs(date).format('MMM YYYY') : ''
}

async function loadRepos() {
  try {
    const [models, datasets, spaces] = await Promise.all([
      repoAPI.listRepos('model', { author: username.value }),
      repoAPI.listRepos('dataset', { author: username.value }),
      repoAPI.listRepos('space', { author: username.value })
    ])
    
    repos.value = {
      model: models.data,
      dataset: datasets.data,
      space: spaces.data
    }
  } catch (err) {
    console.error('Failed to load repos:', err)
  }
}

onMounted(() => {
  loadRepos()
})
</script>