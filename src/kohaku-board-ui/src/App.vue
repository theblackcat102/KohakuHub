<script setup>
import { ref, onMounted } from "vue";
import { initializeSliderSync } from "@/composables/useSliderSync";
import { useAnimationPreference } from "@/composables/useAnimationPreference";
import { getSystemInfo } from "@/utils/api";

const darkMode = ref(false);
const { animationsEnabled, toggleAnimations } = useAnimationPreference();
const systemInfo = ref(null);

onMounted(async () => {
  const savedTheme = localStorage.getItem("theme");
  darkMode.value =
    savedTheme === "dark" ||
    (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  updateTheme();

  // Initialize global slider synchronization
  initializeSliderSync();

  // Fetch system info for mode detection
  try {
    systemInfo.value = await getSystemInfo();
  } catch (error) {
    console.error("Failed to fetch system info:", error);
  }
});

function toggleDarkMode() {
  darkMode.value = !darkMode.value;
  updateTheme();
}

function updateTheme() {
  if (darkMode.value) {
    document.documentElement.classList.add("dark");
    localStorage.setItem("theme", "dark");
  } else {
    document.documentElement.classList.remove("dark");
    localStorage.setItem("theme", "light");
  }
}
</script>

<template>
  <div
    class="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors"
  >
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
            <router-link
              to="/experiments"
              class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-blue-600 dark:hover:text-blue-400"
            >
              Experiments (Legacy)
            </router-link>
          </div>
        </div>
        <div class="flex items-center gap-2">
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
    <main class="max-w-full mx-auto px-6 py-6">
      <router-view />
    </main>
  </div>
</template>

<style>
/* Global animation control */
.no-animations,
.no-animations *,
.no-animations *::before,
.no-animations *::after {
  animation-duration: 0.01ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 0.01ms !important;
  transition-delay: 0ms !important;
}

/* Also respect system preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    transition-delay: 0ms !important;
  }
}
</style>
