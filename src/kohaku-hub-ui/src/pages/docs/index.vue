<!-- Documentation main index page -->
<script setup>
const mainSections = [
  {
    title: "Getting Started",
    description: "Installation, first repository, CLI tools, Python libraries",
    path: "/docs/getting-started",
    icon: "i-carbon-rocket",
    color: "text-blue-600 dark:text-blue-400",
  },
  {
    title: "Features",
    description: "Core features, collaboration, LFS, quotas, organizations",
    path: "/docs/features",
    icon: "i-carbon-cube",
    color: "text-purple-600 dark:text-purple-400",
  },
  {
    title: "Non-Commercial Features",
    description: "Dataset Viewer, KohakuBoard (experiment tracking)",
    path: "/docs/non-commercial",
    icon: "i-carbon-analytics",
    color: "text-pink-600 dark:text-pink-400",
  },
  {
    title: "Deployment",
    description: "Docker, production, security, scaling, backups",
    path: "/docs/deployment",
    icon: "i-carbon-cloud",
    color: "text-green-600 dark:text-green-400",
  },
  {
    title: "API Reference",
    description: "Authentication, repositories, users/orgs, admin endpoints",
    path: "/docs/api",
    icon: "i-carbon-api",
    color: "text-orange-600 dark:text-orange-400",
  },
  {
    title: "Configuration",
    description: "Ports, environment variables, all settings reference",
    path: "/docs/reference",
    icon: "i-carbon-settings",
    color: "text-red-600 dark:text-red-400",
  },
];

const legacyDocs = [
  {
    title: "Setup Guide",
    path: "/docs/setup",
    icon: "i-carbon-document",
  },
  {
    title: "CLI Tools",
    path: "/docs/CLI",
    icon: "i-carbon-terminal",
  },
  { title: "Git Clone", path: "/docs/Git", icon: "i-carbon-code" },
  {
    title: "Admin Portal",
    path: "/docs/Admin",
    icon: "i-carbon-security",
  },
  {
    title: "Port Reference",
    path: "/docs/ports",
    icon: "i-carbon-network-3",
  },
  {
    title: "Contributing",
    path: "/docs/contributing",
    icon: "i-carbon-collaborate",
  },
];
</script>

<template>
  <div class="container-main py-12">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <h1 class="text-4xl font-bold mb-4">Documentation</h1>
        <p class="text-xl text-gray-600 dark:text-gray-400">
          Everything you need to know about KohakuHub
        </p>
      </div>

      <!-- Main Sections (Nested Docs) -->
      <h2 class="text-2xl font-bold mb-6">📚 Documentation Sections</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        <router-link
          v-for="section in mainSections"
          :key="section.path"
          :to="section.path"
          class="card hover:shadow-lg transition-all p-6 cursor-pointer hover:scale-105"
        >
          <div class="flex items-center gap-3 mb-3">
            <div :class="[section.icon, section.color]" class="text-4xl" />
            <h3 class="text-xl font-bold">{{ section.title }}</h3>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            {{ section.description }}
          </p>
        </router-link>
      </div>

      <!-- Legacy Docs -->
      <h2 class="text-2xl font-bold mb-6">📄 Additional Guides</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
        <router-link
          v-for="doc in legacyDocs"
          :key="doc.path"
          :to="doc.path"
          class="card hover:shadow-md p-4 cursor-pointer flex items-center gap-3"
        >
          <div
            :class="doc.icon"
            class="text-2xl text-gray-600 dark:text-gray-400"
          />
          <span class="font-semibold">{{ doc.title }}</span>
        </router-link>
      </div>

      <!-- Quick Links -->
      <div class="card p-6">
        <h2 class="text-2xl font-bold mb-4">Quick Links</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="https://discord.gg/xWYrkyvJ2s"
            target="_blank"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-logo-discord" />
            Join Discord
          </a>
          <a
            href="https://github.com/KohakuBlueleaf/KohakuHub"
            target="_blank"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-logo-github" />
            GitHub
          </a>
          <router-link
            to="/get-started"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-rocket" />
            Get Started
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
