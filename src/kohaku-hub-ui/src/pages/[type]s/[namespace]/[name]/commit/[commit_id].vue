<!-- src/pages/[type]s/[namespace]/[name]/commit/[commit_id].vue -->
<template>
  <div class="container-main">
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <el-icon class="is-loading" size="48">
        <div class="i-carbon-circle-dash" />
      </el-icon>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-20">
      <div class="i-carbon-warning text-6xl text-red-500 mb-4 inline-block" />
      <h2 class="text-2xl font-bold mb-2">Failed to Load Commit</h2>
      <p class="text-gray-600 dark:text-gray-400">{{ error }}</p>
      <el-button type="primary" @click="$router.back()" class="mt-4">
        Go Back
      </el-button>
    </div>

    <!-- Commit Details -->
    <div v-else-if="commitData">
      <!-- Header -->
      <div class="card mb-6">
        <div class="flex items-start gap-4 mb-4">
          <div class="i-carbon-commit text-4xl text-blue-500 flex-shrink-0" />
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold mb-2 break-words">
              {{ commitData.message }}
            </h1>
            <div class="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
              <div class="flex items-center gap-2">
                <div class="i-carbon-user-avatar" />
                <RouterLink
                  :to="`/${commitData.author}`"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {{ commitData.author }}
                </RouterLink>
              </div>
              <div class="flex items-center gap-2">
                <div class="i-carbon-time" />
                {{ formatDate(commitData.date) }}
              </div>
              <div class="flex items-center gap-2">
                <div class="i-carbon-id" />
                <code class="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs">
                  {{ commitData.commit_id?.substring(0, 8) }}
                </code>
              </div>
            </div>
            <div v-if="commitData.description" class="mt-3 text-gray-700 dark:text-gray-300">
              {{ commitData.description }}
            </div>
          </div>
        </div>

        <!-- Parent commit link -->
        <div v-if="commitData.parent_commit" class="pt-3 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center gap-2 text-sm">
            <span class="text-gray-600 dark:text-gray-400">Parent:</span>
            <code class="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs">
              {{ commitData.parent_commit?.substring(0, 8) }}
            </code>
          </div>
        </div>
      </div>

      <!-- Files Changed -->
      <div class="card">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <div class="i-carbon-document text-blue-500" />
          Files Changed
          <el-tag type="info" size="small">{{ commitData.files?.length || 0 }}</el-tag>
        </h2>

        <div v-if="!commitData.files || commitData.files.length === 0" class="text-center py-12 text-gray-500 dark:text-gray-400">
          <div class="i-carbon-document-blank text-6xl mb-4 inline-block" />
          <p>No files changed in this commit</p>
        </div>

        <el-collapse v-else class="commit-diff-collapse">
          <el-collapse-item
            v-for="file in commitData.files"
            :key="file.path"
            :name="file.path"
          >
            <!-- File header (custom title slot) -->
            <template #title>
              <div class="flex items-center gap-3 flex-1 py-1">
                <!-- Change type badge -->
                <el-tag
                  :type="getChangeType(file.type).type"
                  size="small"
                  class="flex-shrink-0"
                >
                  {{ getChangeType(file.type).label }}
                </el-tag>

                <!-- File path -->
                <code class="text-sm font-mono flex-1 truncate">{{ file.path }}</code>

                <!-- Badges -->
                <div class="flex items-center gap-2 flex-shrink-0">
                  <el-tag v-if="file.is_lfs" type="warning" size="small">LFS</el-tag>
                  <el-tag v-if="file.diff" type="info" size="small">Diff</el-tag>
                </div>

                <!-- Size change -->
                <span class="text-xs text-gray-500 flex-shrink-0">
                  <span v-if="file.previous_size && file.size_bytes !== file.previous_size">
                    {{ formatBytes(file.previous_size) }} → {{ formatBytes(file.size_bytes) }}
                  </span>
                  <span v-else>
                    {{ formatBytes(file.size_bytes) }}
                  </span>
                </span>
              </div>
            </template>

            <!-- File diff content -->
            <div class="p-4 bg-gray-50 dark:bg-gray-900">
              <!-- Text file diff (if diff is available) -->
              <div v-if="file.diff && isTextRenderable(file.diff)" class="diff-viewer">
                <pre class="text-xs overflow-x-auto p-4 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700"><code v-html="renderDiff(file.diff)"></code></pre>
              </div>

              <!-- LFS/Binary file metadata -->
              <div v-else-if="file.is_lfs || !file.diff" class="space-y-3">
                <div class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  {{ file.is_lfs ? 'Large File (LFS)' : 'Binary File' }}
                </div>

                <!-- Previous state (for changed/removed) -->
                <div v-if="file.previous_sha256 || file.previous_size" class="space-y-2">
                  <div class="text-xs font-semibold text-gray-600 dark:text-gray-400">
                    Before:
                  </div>
                  <div class="bg-red-50 dark:bg-red-900/20 p-3 rounded border border-red-200 dark:border-red-800">
                    <div v-if="file.previous_size" class="text-sm mb-2">
                      <span class="text-gray-600 dark:text-gray-400">Size:</span>
                      <code class="ml-2 text-red-700 dark:text-red-400">{{ formatBytes(file.previous_size) }}</code>
                    </div>
                    <div v-if="file.previous_sha256" class="text-sm">
                      <span class="text-gray-600 dark:text-gray-400">SHA256:</span>
                      <code class="ml-2 font-mono text-xs text-red-700 dark:text-red-400 break-all">{{ file.previous_sha256 }}</code>
                    </div>
                  </div>
                </div>

                <!-- Current state (for added/changed) -->
                <div v-if="file.sha256 || file.size_bytes" class="space-y-2">
                  <div class="text-xs font-semibold text-gray-600 dark:text-gray-400">
                    After:
                  </div>
                  <div class="bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-800">
                    <div v-if="file.size_bytes" class="text-sm mb-2">
                      <span class="text-gray-600 dark:text-gray-400">Size:</span>
                      <code class="ml-2 text-green-700 dark:text-green-400">{{ formatBytes(file.size_bytes) }}</code>
                    </div>
                    <div v-if="file.sha256" class="text-sm">
                      <span class="text-gray-600 dark:text-gray-400">SHA256:</span>
                      <code class="ml-2 font-mono text-xs text-green-700 dark:text-green-400 break-all">{{ file.sha256 }}</code>
                    </div>
                  </div>
                </div>

                <!-- View file button -->
                <div v-if="file.type !== 'removed'" class="mt-3">
                  <el-button
                    size="small"
                    @click="viewFile(file.path)"
                    :icon="'View'"
                  >
                    View File
                  </el-button>
                </div>
              </div>

              <!-- Added files (no previous content) -->
              <div v-else-if="file.type === 'added'">
                <div class="text-xs text-green-600 dark:text-green-400 mb-2">
                  New file created
                </div>
                <el-button
                  size="small"
                  @click="viewFile(file.path)"
                  :icon="'View'"
                >
                  View File
                </el-button>
              </div>

              <!-- Removed files -->
              <div v-else-if="file.type === 'removed'">
                <div class="text-xs text-red-600 dark:text-red-400">
                  File deleted
                </div>
              </div>

              <!-- Fallback for files too large or diff unavailable -->
              <div v-else class="text-xs text-gray-500">
                <div class="mb-2">
                  {{ file.size_bytes > 1000000 ? 'File too large to show diff (>1MB)' : 'Diff not available' }}
                </div>
                <el-button
                  v-if="file.type !== 'removed'"
                  size="small"
                  @click="viewFile(file.path)"
                  :icon="'View'"
                >
                  View File
                </el-button>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

const route = useRoute()
const router = useRouter()

const type = computed(() => route.params.type)
const namespace = computed(() => route.params.namespace)
const name = computed(() => route.params.name)
const commitId = computed(() => route.params.commit_id)
const repoId = computed(() => `${namespace.value}/${name.value}`)

const loading = ref(true)
const error = ref(null)
const commitData = ref(null)

async function loadCommitDetails() {
  loading.value = true
  error.value = null

  try {
    // Fetch commit detail
    const detailResponse = await axios.get(
      `/api/${type.value}s/${namespace.value}/${name.value}/commit/${commitId.value}`
    )

    // Fetch commit diff
    const diffResponse = await axios.get(
      `/api/${type.value}s/${namespace.value}/${name.value}/commit/${commitId.value}/diff`
    )

    commitData.value = {
      ...detailResponse.data,
      ...diffResponse.data,
    }
  } catch (err) {
    console.error('Failed to load commit:', err)
    error.value = err.response?.data?.detail?.error || 'Failed to load commit details'
  } finally {
    loading.value = false
  }
}

function formatDate(timestamp) {
  if (!timestamp) return 'Unknown'
  return dayjs.unix(timestamp).format('YYYY-MM-DD HH:mm:ss')
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1000
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getChangeType(type) {
  switch (type) {
    case 'added':
      return { label: 'Added', type: 'success' }
    case 'removed':
      return { label: 'Removed', type: 'danger' }
    case 'changed':
      return { label: 'Modified', type: 'warning' }
    default:
      return { label: type, type: 'info' }
  }
}

function viewFile(path) {
  router.push(`/${type.value}s/${namespace.value}/${name.value}/blob/main/${path}`)
}

function isTextRenderable(diff) {
  // Check if diff contains mostly printable characters
  if (!diff) return false

  // Simple heuristic: if less than 5% null bytes, consider it text
  const nullBytes = (diff.match(/\x00/g) || []).length
  return nullBytes < diff.length * 0.05
}

function renderDiff(diff) {
  if (!diff) return ''

  // Escape HTML
  const escaped = diff
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Color diff lines
  const lines = escaped.split('\n')
  const colored = lines.map(line => {
    if (line.startsWith('+') && !line.startsWith('+++')) {
      return `<span style="color: #22c55e; background: rgba(34, 197, 94, 0.1);">${line}</span>`
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      return `<span style="color: #ef4444; background: rgba(239, 68, 68, 0.1);">${line}</span>`
    } else if (line.startsWith('@@')) {
      return `<span style="color: #3b82f6; font-weight: 600;">${line}</span>`
    } else if (line.startsWith('+++') || line.startsWith('---')) {
      return `<span style="color: #6b7280; font-weight: 600;">${line}</span>`
    } else {
      return line
    }
  })

  return colored.join('\n')
}

onMounted(() => {
  loadCommitDetails()
})
</script>

<style scoped>
.is-loading {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Diff viewer styling */
:deep(.commit-diff-collapse .el-collapse-item__header) {
  font-family: inherit;
  padding: 12px 16px;
  background: transparent;
}

:deep(.commit-diff-collapse .el-collapse-item__wrap) {
  border: none;
}

:deep(.commit-diff-collapse .el-collapse-item__content) {
  padding: 0;
}

.diff-viewer {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* Syntax highlighting for diff */
.diff-viewer :deep(code) {
  display: block;
  white-space: pre;
  color: inherit;
}

/* Diff line colors */
:deep(.diff-viewer code) {
  background: transparent !important;
}
</style>
