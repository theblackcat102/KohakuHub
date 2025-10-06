<!-- src/pages/docs/index.vue -->
<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

const docs = [
  {
    title: "Setup Guide",
    description:
      "Step-by-step installation and configuration guide. Learn how to deploy KohakuHub with Docker and customize it for your needs.",
    path: "/docs/setup",
    icon: "i-carbon-rocket",
  },
  {
    title: "Deployment Architecture",
    description:
      "Understanding KohakuHub's architecture, port configuration, and nginx reverse proxy setup. Essential for production deployments.",
    path: "/docs/deployment",
    icon: "i-carbon-cloud",
  },
  {
    title: "Port Reference",
    description:
      "Quick reference guide for all ports used by KohakuHub services. Know which port to use for what.",
    path: "/docs/ports",
    icon: "i-carbon-network-3",
  },
  {
    title: "API Documentation",
    description:
      "Learn about KohakuHub's API, data flow, and key endpoints. Includes detailed workflow diagrams for uploads, downloads, and repository management.",
    path: "/docs/api",
    icon: "i-carbon-api",
  },
  {
    title: "CLI Documentation",
    description:
      "Complete guide to the kohub-cli tool. Covers both Python API and command-line interface for managing repositories, organizations, and more.",
    path: "/docs/cli",
    icon: "i-carbon-terminal",
  },
  {
    title: "Contributing & Roadmap",
    description:
      "Want to contribute? Learn how to set up, code style guidelines, and see the project roadmap with current status and planned features.",
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

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <router-link
          v-for="doc in docs"
          :key="doc.path"
          :to="doc.path"
          class="card hover:shadow-lg transition-shadow duration-200 p-6 cursor-pointer"
        >
          <div class="flex items-start gap-4">
            <div
              :class="doc.icon"
              class="text-3xl text-primary-600 dark:text-primary-400 flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <h2 class="text-xl font-semibold mb-2">{{ doc.title }}</h2>
              <p class="text-gray-600 dark:text-gray-400">
                {{ doc.description }}
              </p>
            </div>
          </div>
        </router-link>
      </div>

      <div class="mt-12 card p-6">
        <h2 class="text-2xl font-bold mb-4">Quick Links</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="https://discord.gg/xWYrkyvJ2s"
            target="_blank"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-logo-discord" />
            Join our Discord
          </a>
          <a
            href="https://github.com/KohakuBlueleaf/KohakuHub"
            target="_blank"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-logo-github" />
            GitHub Repository
          </a>
          <router-link
            to="/get-started"
            class="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:underline"
          >
            <div class="i-carbon-rocket" />
            Get Started Guide
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
