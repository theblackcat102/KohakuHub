<!-- Single unified documentation handler -->
<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const route = useRoute();
const content = ref("");
const isDirectory = ref(false);
const directoryDocs = ref([]);
const loading = ref(true);

// Main doc sections
const mainSections = [
  {
    title: "Getting Started",
    description: "Installation, first repository, CLI tools, Python libraries",
    path: "getting-started",
    icon: "i-carbon-rocket",
    color: "text-blue-600 dark:text-blue-400",
  },
  {
    title: "Features",
    description: "LFS, quotas, fallback, metadata, organizations, invitations",
    path: "features",
    icon: "i-carbon-cube",
    color: "text-purple-600 dark:text-purple-400",
  },
  {
    title: "Deployment",
    description: "Docker setup, production config, security, scaling",
    path: "deployment",
    icon: "i-carbon-cloud",
    color: "text-green-600 dark:text-green-400",
  },
  {
    title: "API Reference",
    description: "Authentication, repositories, users/orgs, admin",
    path: "api",
    icon: "i-carbon-api",
    color: "text-orange-600 dark:text-orange-400",
  },
  {
    title: "Configuration",
    description: "Ports, environment variables, all settings",
    path: "reference",
    icon: "i-carbon-settings",
    color: "text-red-600 dark:text-red-400",
  },
];

// Legacy flat docs
const legacyDocs = [
  { title: "Setup", file: "setup.md", icon: "i-carbon-document" },
  { title: "CLI", file: "CLI.md", icon: "i-carbon-terminal" },
  { title: "Git", file: "Git.md", icon: "i-carbon-code" },
  { title: "Admin", file: "Admin.md", icon: "i-carbon-security" },
  { title: "Ports", file: "ports.md", icon: "i-carbon-network-3" },
  { title: "API", file: "API.md", icon: "i-carbon-api" },
  {
    title: "Contributing",
    file: "contributing.md",
    icon: "i-carbon-collaborate",
  },
];

function parseFrontmatter(markdown) {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n/;
  const match = markdown.match(frontmatterRegex);
  if (!match) return { title: null, description: null, icon: null };

  const yamlLines = match[1].split("\n");
  const meta = {};
  for (const line of yamlLines) {
    const [key, ...valueParts] = line.split(":");
    if (key && valueParts.length) {
      meta[key.trim()] = valueParts.join(":").trim();
    }
  }
  return {
    title: meta.title || null,
    description: meta.description || null,
    icon: meta.icon || null,
  };
}

function getDocIcon(filename) {
  const iconMap = {
    lfs: "i-carbon-data-volume",
    quotas: "i-carbon-meter",
    fallback: "i-carbon-connect",
    metadata: "i-carbon-information",
    organizations: "i-carbon-group",
    invitations: "i-carbon-email",
    branches: "i-carbon-branch",
    "likes-trending": "i-carbon-favorite",
    authentication: "i-carbon-password",
    repositories: "i-carbon-data-base",
    admin: "i-carbon-security",
    docker: "i-carbon-container-services",
    production: "i-carbon-cloud-upload",
    config: "i-carbon-settings-adjust",
    ports: "i-carbon-network-3",
  };
  const name = filename.replace(".md", "").toLowerCase();
  return iconMap[name] || "i-carbon-document";
}

async function loadDoc() {
  loading.value = true;
  const pathSegments = route.path.split("/").filter(Boolean);

  // Root /docs - show main index
  if (pathSegments.length === 1 && pathSegments[0] === "docs") {
    isDirectory.value = true;
    directoryDocs.value = [];
    loading.value = false;
    return;
  }

  // Get doc path (everything after /docs/)
  const docPath = pathSegments.slice(1).join("/");

  try {
    // Try as file
    const fileResponse = await fetch(`/documentation/${docPath}.md`);
    if (fileResponse.ok) {
      const text = await fileResponse.text();

      // Check if it's HTML (SPA fallback) instead of markdown
      if (
        text.trim().startsWith("<!DOCTYPE") ||
        text.trim().startsWith("<!doctype") ||
        text.trim().startsWith("<html")
      ) {
        // Not a real file, try directory
      } else {
        content.value = text;
        isDirectory.value = false;
        loading.value = false;
        return;
      }
    }

    // Try as directory (load manifest)
    const manifestResponse = await fetch(
      `/documentation/${docPath}/.manifest.json`,
    );
    if (manifestResponse.ok) {
      const manifestText = await manifestResponse.text();

      // Check if manifest is HTML
      if (
        manifestText.trim().startsWith("<!DOCTYPE") ||
        manifestText.trim().startsWith("<html")
      ) {
        throw new Error("Directory not found");
      }

      const files = JSON.parse(manifestText);

      // Load frontmatter from each file
      const docsWithMeta = await Promise.all(
        files.map(async (filename) => {
          try {
            const response = await fetch(
              `/documentation/${docPath}/${filename}`,
            );
            const markdown = await response.text();

            // Skip if HTML
            if (
              markdown.trim().startsWith("<!DOCTYPE") ||
              markdown.trim().startsWith("<html")
            ) {
              return null;
            }

            const { title, description, icon } = parseFrontmatter(markdown);

            return {
              filename,
              title: title || filename.replace(".md", "").replace(/-/g, " "),
              description: description || "",
              path: `/docs/${docPath}/${filename.replace(".md", "")}`,
              icon: icon || getDocIcon(filename), // Use frontmatter icon or fallback
            };
          } catch {
            return null;
          }
        }),
      );

      directoryDocs.value = docsWithMeta.filter((d) => d !== null);
      isDirectory.value = true;
      loading.value = false;
      return;
    }

    // Not found
    content.value = `# Documentation Not Found\n\n[← Back to Documentation](/docs)`;
    isDirectory.value = false;
  } catch (e) {
    content.value = `# Error\n\n${e.message}\n\n[← Back](/docs)`;
    isDirectory.value = false;
  }

  loading.value = false;
}

onMounted(() => loadDoc());
watch(
  () => route.path,
  () => loadDoc(),
);
</script>

<template>
  <div v-if="loading" class="container-main py-12 text-center">
    <div
      class="i-carbon-circle-dash animate-spin text-4xl text-gray-400 mb-4"
    />
    <p>Loading documentation...</p>
  </div>

  <!-- Main Index -->
  <div
    v-else-if="isDirectory && directoryDocs.length === 0"
    class="container-main py-12"
  >
    <div class="max-w-6xl mx-auto">
      <h1 class="text-4xl font-bold mb-4">Documentation</h1>
      <p class="text-xl text-gray-600 dark:text-gray-400 mb-8">
        Everything you need to know about KohakuHub
      </p>

      <!-- Main Sections -->
      <h2 class="text-2xl font-bold mb-6">📚 Documentation Sections</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        <router-link
          v-for="section in mainSections"
          :key="section.path"
          :to="`/docs/${section.path}`"
          class="card hover:shadow-lg transition-all p-6 cursor-pointer"
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
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <a
          v-for="doc in legacyDocs"
          :key="doc.file"
          :href="`/documentation/${doc.file}`"
          target="_blank"
          class="card hover:shadow-md p-4 cursor-pointer"
        >
          <div class="flex items-center gap-3">
            <div
              :class="doc.icon"
              class="text-2xl text-gray-600 dark:text-gray-400"
            />
            <span class="font-semibold">{{ doc.title }}</span>
          </div>
        </a>
      </div>
    </div>
  </div>

  <!-- Directory Listing -->
  <div v-else-if="isDirectory" class="container-main py-12">
    <div class="max-w-6xl mx-auto">
      <h1 class="text-4xl font-bold mb-8 capitalize">
        {{ route.path.split("/").pop() }}
      </h1>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <router-link
          v-for="doc in directoryDocs"
          :key="doc.path"
          :to="doc.path"
          class="card hover:shadow-lg transition-shadow p-6 cursor-pointer"
        >
          <div class="flex items-start gap-3">
            <div
              :class="doc.icon"
              class="text-3xl text-primary-600 dark:text-primary-400"
            />
            <div>
              <h3 class="text-xl font-bold mb-2">{{ doc.title }}</h3>
              <p
                v-if="doc.description"
                class="text-sm text-gray-600 dark:text-gray-400"
              >
                {{ doc.description }}
              </p>
            </div>
          </div>
        </router-link>
      </div>

      <div class="mt-8">
        <router-link
          to="/docs"
          class="text-primary-600 dark:text-primary-400 hover:underline"
        >
          ← Back to Documentation
        </router-link>
      </div>
    </div>
  </div>

  <!-- Markdown Content -->
  <MarkdownPage v-else :content="content" />
</template>
