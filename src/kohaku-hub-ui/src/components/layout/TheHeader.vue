<!-- src/kohaku-hub-ui/src/components/layout/TheHeader.vue -->
<template>
  <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
    <div class="container-main flex items-center justify-between h-16">
      <!-- Logo -->
      <RouterLink to="/" class="flex items-center gap-2">
        <div class="i-carbon-cube text-3xl text-blue-500" />
        <span class="text-xl font-bold">KohakuHub</span>
      </RouterLink>
      
      <!-- Navigation -->
      <nav class="flex items-center gap-6">
        <RouterLink to="/models" class="text-gray-700 hover:text-blue-500">
          Models
        </RouterLink>
        <RouterLink to="/datasets" class="text-gray-700 hover:text-blue-500">
          Datasets
        </RouterLink>
        <RouterLink to="/spaces" class="text-gray-700 hover:text-blue-500">
          Spaces
        </RouterLink>
      </nav>
      
      <!-- User Menu -->
      <div class="flex items-center gap-4">
        <template v-if="isAuthenticated">
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
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()
const { isAuthenticated, username } = storeToRefs(authStore)
const router = useRouter()

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