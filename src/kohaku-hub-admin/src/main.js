import { createApp } from "vue";
import { createPinia } from "pinia";
import { createRouter, createWebHistory } from "vue-router";
import { routes } from "vue-router/auto-routes";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "uno.css";
import "./style.css";
import App from "./App.vue";

const app = createApp(App);
const pinia = createPinia();

const router = createRouter({
  history: createWebHistory("/admin/"),
  routes,
});

app.use(pinia);
app.use(router);
app.use(ElementPlus);

app.mount("#app");
