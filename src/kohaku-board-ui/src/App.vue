<script setup>
import { ref, onMounted } from "vue";

const darkMode = ref(false);

onMounted(() => {
  const savedTheme = localStorage.getItem("theme");
  darkMode.value =
    savedTheme === "dark" ||
    (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  updateTheme();
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
            <img src="/images/logo-square.svg" alt="KohakuBoard" class="h-8 w-8" />
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
              Dashboard
            </router-link>
            <router-link
              to="/experiments"
              class="px-3 py-1.5 rounded-md text-sm font-medium transition-colors text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-blue-600 dark:hover:text-blue-400"
            >
              Experiments
            </router-link>
          </div>
        </div>
        <button
          @click="toggleDarkMode"
          class="p-2 rounded-md transition-colors bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-lg"
        >
          <span v-if="darkMode">☀️</span>
          <span v-else>🌙</span>
        </button>
      </div>
    </nav>
    <main class="max-w-full mx-auto px-6 py-6">
      <router-view />
    </main>
  </div>
</template>
