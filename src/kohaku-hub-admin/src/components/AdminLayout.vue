<script setup>
import { useRouter, useRoute } from "vue-router";
import { useAdminStore } from "@/stores/admin";
import { useThemeStore } from "@/stores/theme";
import { ElMessage } from "element-plus";

const router = useRouter();
const route = useRoute();
const adminStore = useAdminStore();
const themeStore = useThemeStore();

function handleLogout() {
  adminStore.logout();
  ElMessage.success("Logged out successfully");
  router.push("/login");
}

const menuItems = [
  { path: "/", label: "Dashboard", icon: "i-carbon-dashboard" },
  { path: "/users", label: "Users", icon: "i-carbon-user-multiple" },
  { path: "/repositories", label: "Repositories", icon: "i-carbon-data-base" },
  { path: "/commits", label: "Commits", icon: "i-carbon-git-commit" },
  { path: "/storage", label: "Storage", icon: "i-carbon-data-volume" },
  { path: "/quotas", label: "Quotas", icon: "i-carbon-meter" },
];
</script>

<template>
  <el-container class="admin-layout">
    <!-- Sidebar -->
    <el-aside width="250px" class="sidebar">
      <div class="sidebar-header">
        <div
          class="i-carbon-security text-2xl text-blue-600 dark:text-blue-400"
        />
        <h2 class="text-xl font-bold ml-2 text-gray-900 dark:text-gray-100">
          Admin Portal
        </h2>
      </div>

      <el-menu
        :default-active="route.path"
        router
        class="sidebar-menu"
        :background-color="themeStore.isDark ? '#1f1f1f' : '#ffffff'"
        :text-color="themeStore.isDark ? '#e0e0e0' : '#303133'"
        :active-text-color="'#409EFF'"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <div :class="item.icon" class="mr-2" />
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main Content -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-title">
          <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
            KohakuHub Administration
          </h1>
        </div>

        <div class="header-actions">
          <el-button circle @click="themeStore.toggle()" class="mr-2">
            <div v-if="themeStore.isDark" class="i-carbon-moon text-lg" />
            <div v-else class="i-carbon-asleep text-lg" />
          </el-button>
          <el-button type="danger" @click="handleLogout" :icon="'SwitchButton'">
            Logout
          </el-button>
        </div>
      </el-header>

      <!-- Content -->
      <el-main class="main-content">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.sidebar {
  background-color: white;
  border-right: 1px solid #e5e7eb;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

html.dark .sidebar {
  background-color: #1f1f1f;
  border-right-color: #374151;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

html.dark .sidebar-header {
  border-bottom-color: #374151;
}

.sidebar-menu {
  border-right: none;
}

.header {
  background-color: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

html.dark .header {
  background-color: #1f1f1f;
  border-bottom-color: #374151;
}

.header-title {
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
}

.main-content {
  background-color: #f5f5f5;
  min-height: calc(100vh - 60px);
}

html.dark .main-content {
  background-color: #0a0a0a;
}
</style>
