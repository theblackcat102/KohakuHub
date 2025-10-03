<!-- src/kohaku-hub-ui/src/pages/settings.vue -->
<template>
  <div class="container-main">
    <h1 class="text-3xl font-bold mb-6">Settings</h1>
    
    <el-tabs v-model="activeTab">
      <!-- Profile -->
      <el-tab-pane label="Profile" name="profile">
        <div class="max-w-2xl">
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Profile Information</h2>
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium mb-1">Username</label>
                <el-input :value="user?.username" disabled />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Email</label>
                <el-input :value="user?.email" disabled />
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- API Tokens -->
      <el-tab-pane label="API Tokens" name="tokens">
        <div class="max-w-2xl">
          <div class="card mb-4">
            <h2 class="text-xl font-semibold mb-4">Create New Token</h2>
            <div class="flex gap-2">
              <el-input
                v-model="newTokenName"
                placeholder="Token name (e.g., my-laptop)"
              />
              <el-button type="primary" @click="handleCreateToken">
                Create Token
              </el-button>
            </div>
          </div>
          
          <div v-if="newToken" class="card mb-4 bg-yellow-50">
            <h3 class="font-semibold mb-2">New Token Created</h3>
            <p class="text-sm text-gray-600 mb-2">
              Make sure to copy your token now. You won't be able to see it again!
            </p>
            <el-input
              :value="newToken"
              readonly
              class="font-mono"
            >
              <template #append>
                <el-button @click="copyToken">
                  <div class="i-carbon-copy" />
                </el-button>
              </template>
            </el-input>
          </div>
          
          <div class="card">
            <h2 class="text-xl font-semibold mb-4">Active Tokens</h2>
            <div class="space-y-2">
              <div
                v-for="token in tokens"
                :key="token.id"
                class="flex items-center justify-between p-3 border border-gray-200 rounded"
              >
                <div>
                  <div class="font-medium">{{ token.name }}</div>
                  <div class="text-sm text-gray-600">
                    Created {{ formatDate(token.created_at) }}
                  </div>
                </div>
                <el-button
                  type="danger"
                  text
                  @click="handleRevokeToken(token.id)"
                >
                  Revoke
                </el-button>
              </div>
              
              <div v-if="!tokens || tokens.length === 0" class="text-center py-8 text-gray-500">
                No active tokens
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { authAPI } from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

const activeTab = ref('profile')
const newTokenName = ref('')
const newToken = ref('')
const tokens = ref([])

function formatDate(date) {
  return dayjs(date).format('MMM D, YYYY')
}

async function loadTokens() {
  try {
    const { data } = await authAPI.listTokens()
    tokens.value = data.tokens
  } catch (err) {
    console.error('Failed to load tokens:', err)
  }
}

async function handleCreateToken() {
  if (!newTokenName.value) {
    ElMessage.warning('Please enter token name')
    return
  }
  
  try {
    const { data } = await authAPI.createToken({ name: newTokenName.value })
    newToken.value = data.token
    newTokenName.value = ''
    await loadTokens()
    ElMessage.success('Token created')
  } catch (err) {
    ElMessage.error('Failed to create token')
  }
}

async function handleRevokeToken(id) {
  try {
    await ElMessageBox.confirm(
      'This will permanently delete the token. Continue?',
      'Warning',
      { type: 'warning' }
    )
    
    await authAPI.revokeToken(id)
    await loadTokens()
    ElMessage.success('Token revoked')
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Failed to revoke token')
    }
  }
}

function copyToken() {
  navigator.clipboard.writeText(newToken.value)
  ElMessage.success('Token copied to clipboard')
}

onMounted(() => {
  loadTokens()
})
</script>