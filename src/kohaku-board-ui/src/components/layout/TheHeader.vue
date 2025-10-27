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

const { animationsEnabled, toggleAnimations } = useAnimationPreference();

const props = defineProps({
  darkMode: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["toggle-dark-mode"]);

function toggleDarkMode() {
  emit("toggle-dark-mode");
}
</script>
