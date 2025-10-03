// src/kohaku-hub-ui/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import { routes } from 'vue-router/auto-routes'
import App from './App.vue'

// Import UnoCSS
import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'

// Import Element Plus base styles
import 'element-plus/dist/index.css'

const app = createApp(App)

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes
})

app.use(createPinia())
app.use(router)
app.mount('#app')