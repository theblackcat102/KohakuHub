<template>
  <nav
    class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-3 shadow-sm"
  >
    <div class="flex items-center justify-between max-w-full mx-auto">
      <div class="flex items-center gap-6">
        <router-link to="/" class="flex items-center gap-2">
          <img
            src="/images/logo-square.svg"
            alt="KohakuBoard"
            class="h-8 w-8"
          />
          <h1
            class="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent"
          >
            KohakuBoard
          </h1>
        </router-link>
        <div class="flex items-center gap-1">
          <router-link
            to="/"
            class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-blue-600 dark:hover:text-blue-400"
          >
            Projects
          </router-link>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <!-- Auth UI (only in remote mode) -->
        <template v-if="isRemoteMode">
          <template v-if="authStore.isAuthenticated">
            <!-- User dropdown -->
            <el-dropdown>
              <div
                class="flex items-center gap-2 cursor-pointer px-3 py-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <div
                  class="i-ep-user text-xl text-gray-700 dark:text-gray-300"
                />
                <span class="text-sm text-gray-900 dark:text-gray-100">
                  {{ authStore.username }}
                </span>
                <div class="i-ep-arrow-down text-gray-500 dark:text-gray-400" />
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleLogout">
                    <div class="i-ep-switch-button inline-block mr-2" />
                    Logout
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button @click="$router.push('/login')" size="small" plain>
              Login
            </el-button>
            <el-button
              type="primary"
              @click="$router.push('/register')"
              size="small"
            >
              Sign Up
            </el-button>
          </template>
        </template>

        <!-- Theme toggle -->
        <button
          @click="toggleAnimations"
          class="p-2 rounded-md transition-colors bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-lg"
          :title="
            animationsEnabled ? 'Disable animations' : 'Enable animations'
          "
        >
          <span v-if="animationsEnabled">🎬</span>
          <span v-else>⏸️</span>
        </button>
        <button
          @click="toggleDarkMode"
          class="p-2 rounded-md transition-colors bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-lg"
          title="Toggle dark mode"
        >
          <span v-if="darkMode">☀️</span>
          <span v-else>🌙</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useAnimationPreference } from "@/composables/useAnimationPreference";
import { useAuthStore } from "@/stores/auth";
import { getSystemInfo } from "@/utils/api";
import { ElMessage } from "element-plus";

const { animationsEnabled, toggleAnimations } = useAnimationPreference();
const authStore = useAuthStore();
const router = useRouter();
const systemInfo = ref(null);

const props = defineProps({
  darkMode: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["toggle-dark-mode"]);

onMounted(async () => {
  try {
    systemInfo.value = await getSystemInfo();
  } catch (err) {
    console.error("Failed to load system info:", err);
  }
});

const isRemoteMode = computed(() => systemInfo.value?.mode === "remote");

function toggleDarkMode() {
  emit("toggle-dark-mode");
}

async function handleLogout() {
  try {
    await authStore.logout();
    ElMessage.success("Logged out successfully");
    router.push("/");
  } catch (err) {
    ElMessage.error("Logout failed");
  }
}
</script>
