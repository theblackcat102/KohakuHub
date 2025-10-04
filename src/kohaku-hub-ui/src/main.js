// src/kohaku-hub-ui/src/main.js
import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import { routes } from "vue-router/auto-routes";
import App from "./App.vue";

// Import UnoCSS
import "virtual:uno.css";
import "@unocss/reset/tailwind.css";

// Import Element Plus base styles
import "element-plus/dist/index.css";
// Import Element Plus dark theme
import "element-plus/theme-chalk/dark/css-vars.css";

// Import highlight.js theme for syntax highlighting
import "highlight.js/styles/github.css"; // Light theme
import "highlight.js/styles/github-dark.css"; // Dark theme

const app = createApp(App);
const pinia = createPinia();

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes,
});

app.use(pinia);
app.use(router);

// Initialize auth before mounting
import { useAuthStore } from "./stores/auth";
const authStore = useAuthStore();

// Restore auth state, then mount app
authStore.init().finally(() => {
  app.mount("#app");
});
