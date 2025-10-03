<!-- src/components/layout/TheHeader.vue -->
<template>
  <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50 transition-colors">
    <div class="container-main flex items-center justify-between h-12">
      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-2">
        <div class="i-carbon-cube text-3xl text-blue-500" />
        <span class="text-xl font-bold">KohakuHub</span>
      </RouterLink>

      <!-- Navigation -->
      <nav class="flex items-center gap-6">
        <RouterLink to="/models" class="text-gray-700 dark:text-gray-300 hover:text-blue-500 dark:hover:text-blue-400 transition-colors">
          Models
        </RouterLink>
        <RouterLink to="/datasets" class="text-gray-700 dark:text-gray-300 hover:text-blue-500 dark:hover:text-blue-400 transition-colors">
          Datasets
        </RouterLink>
        <RouterLink to="/spaces" class="text-gray-700 dark:text-gray-300 hover:text-blue-500 dark:hover:text-blue-400 transition-colors">
          Spaces
        </RouterLink>
      </nav>

      <!-- User Menu -->
      <div class="flex items-center gap-4">
        <!-- Dark Mode Toggle -->
        <el-button
          @click="themeStore.toggle()"
          circle
          text
          class="!text-gray-700 dark:!text-gray-300"
        >
          <div v-if="themeStore.isDark" class="i-carbon-moon text-xl" />
          <div v-else class="i-carbon-asleep text-xl" />
        </el-button>
        <template v-if="isAuthenticated">
          <!-- Create New Dropdown -->
          <el-dropdown trigger="click">
            <el-button type="primary" circle>
              <div class="i-carbon-add text-xl" />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="createNew('model')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-model text-blue-500" />
                    <span>New Model</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item @click="createNew('dataset')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-data-table text-green-500" />
                    <span>New Dataset</span>
                  </div>
                </el-dropdown-item>
                <el-dropdown-item @click="createNew('space')">
                  <div class="flex items-center gap-2">
                    <div class="i-carbon-application text-purple-500" />
                    <span>New Space</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- User Dropdown -->
          <el-dropdown>
            <div class="flex items-center gap-2 cursor-pointer">
              <div class="i-carbon-user-avatar text-2xl" />
              <span>{{ username }}</span>
              <div class="i-carbon-chevron-down" />
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push(`/${username}`)">
                  <div class="i-carbon-user inline-block mr-2" />
                  Profile
                </el-dropdown-item>
                <el-dropdown-item @click="$router.push('/settings')">
                  <div class="i-carbon-settings inline-block mr-2" />
                  Settings
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <div class="i-carbon-logout inline-block mr-2" />
                  Logout
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        
        <template v-else>
          <el-button @click="$router.push('/login')" text>
            Login
          </el-button>
          <el-button type="primary" @click="$router.push('/register')">
            Sign Up
          </el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const themeStore = useThemeStore()
const { isAuthenticated, username } = storeToRefs(authStore)
const router = useRouter()

function createNew(type) {
  router.push({
    path: '/new',
    query: { type }
  })
}

async function handleLogout() {
  try {
    await authStore.logout()
    ElMessage.success('Logged out successfully')
    router.push('/')
  } catch (err) {
    ElMessage.error('Logout failed')
  }
}
</script>