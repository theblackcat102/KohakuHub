<!-- src/kohaku-hub-ui/src/pages/[type]s/[namespace]/[name]/blob/[branch]/[...file].vue -->
<template>
  <div class="container-main">
    <!-- Breadcrumb -->
    <el-breadcrumb separator="/" class="mb-6 text-gray-700 dark:text-gray-300">
      <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s` }">
        {{ repoTypeLabel }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${namespace}` }">
        {{ namespace }}
      </el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/${repoType}s/${namespace}/${name}` }">
        {{ name }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ fileName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="loading" class="text-center py-20">
      <el-icon class="is-loading" :size="40">
        <div class="i-carbon-loading" />
      </el-icon>
    </div>

    <div v-else-if="error" class="text-center py-20">
      <div class="i-carbon-warning text-6xl text-red-500 mb-4" />
      <h2 class="text-2xl font-bold mb-2">File Not Found</h2>
      <p class="text-gray-600 dark:text-gray-400 mb-4">{{ error }}</p>
      <el-button @click="$router.back()">Go Back</el-button>
    </div>

    <div v-else>
      <!-- File Header -->
      <div class="card mb-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div :class="getFileIcon(fileName)" class="text-3xl" />
            <div>
              <h1 class="text-2xl font-bold">{{ fileName }}</h1>
              <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {{ formatSize(fileSize) }}
                <span v-if="fileSize" class="mx-2">•</span>
                <span>{{ fileExtension || "No extension" }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <el-button @click="copyFileUrl">
              <div class="i-carbon-link inline-block mr-1" />
              Copy URL
            </el-button>
            <el-button type="primary" @click="downloadFile">
              <div class="i-carbon-download inline-block mr-1" />
              Download
            </el-button>
          </div>
        </div>

        <!-- File path breadcrumb -->
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center gap-2 text-sm">
            <el-tag size="small">{{ branch }}</el-tag>
            <span class="text-gray-400 dark:text-gray-500">/</span>
            <el-breadcrumb
              separator="/"
              class="text-gray-700 dark:text-gray-300"
            >
              <el-breadcrumb-item
                v-for="(segment, idx) in pathSegments"
                :key="idx"
              >
                <a
                  v-if="idx < pathSegments.length - 1"
                  @click="
                    navigateToFolder(pathSegments.slice(0, idx + 1).join('/'))
                  "
                  class="cursor-pointer text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {{ segment }}
                </a>
                <span v-else class="text-gray-700 dark:text-gray-300">{{
                  segment
                }}</span>
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
      </div>

      <!-- File Content -->
      <div class="card">
        <!-- Image Preview -->
        <div v-if="isImage" class="text-center">
          <img
            :src="fileUrl"
            :alt="fileName"
            class="max-w-full h-auto mx-auto"
            style="max-height: 800px"
          />
        </div>

        <!-- Video Preview -->
        <div v-else-if="isVideo" class="text-center">
          <video
            :src="fileUrl"
            controls
            class="max-w-full h-auto mx-auto"
            style="max-height: 600px"
          >
            Your browser does not support video playback.
          </video>
        </div>

        <!-- Audio Preview -->
        <div v-else-if="isAudio" class="text-center py-8">
          <div
            class="i-carbon-music text-6xl text-gray-400 mb-4 inline-block"
          />
          <audio :src="fileUrl" controls class="w-full max-w-xl mx-auto" />
        </div>

        <!-- PDF Preview -->
        <div v-else-if="isPDF" class="h-[800px]">
          <iframe
            :src="fileUrl"
            class="w-full h-full border-0"
            title="PDF Preview"
          />
        </div>

        <!-- Text/Code Preview -->
        <div v-else-if="canPreviewText">
          <div
            class="flex items-center justify-between mb-3 pb-3 border-b border-gray-200 dark:border-gray-700"
          >
            <div class="flex items-center gap-2">
              <el-tag size="small" type="info">{{ languageLabel }}</el-tag>
              <span class="text-sm text-gray-600 dark:text-gray-400"
                >{{ lineCount }} lines</span
              >
            </div>
            <el-button size="small" @click="copyContent">
              <div class="i-carbon-copy inline-block mr-1" />
              Copy
            </el-button>
          </div>

          <pre
            class="text-sm overflow-x-auto bg-gray-50 dark:bg-gray-900 p-4 rounded"
          ><code>{{ fileContent }}</code></pre>
        </div>

        <!-- Markdown Preview -->
        <div v-else-if="isMarkdown">
          <div
            class="flex items-center justify-between mb-4 pb-3 border-b border-gray-200 dark:border-gray-700"
          >
            <el-radio-group v-model="markdownView" size="small">
              <el-radio-button label="preview">Preview</el-radio-button>
              <el-radio-button label="source">Source</el-radio-button>
            </el-radio-group>
            <el-button
              v-if="markdownView === 'source'"
              size="small"
              @click="copyContent"
            >
              <div class="i-carbon-copy inline-block mr-1" />
              Copy
            </el-button>
          </div>

          <div v-if="markdownView === 'preview'">
            <MarkdownViewer :content="fileContent" />
          </div>
          <pre
            v-else
            class="text-sm overflow-x-auto bg-gray-50 dark:bg-gray-900 p-4 rounded"
          ><code>{{ fileContent }}</code></pre>
        </div>

        <!-- Too Large / Binary -->
        <div v-else class="text-center py-16">
          <div
            :class="getFileIcon(fileName)"
            class="text-8xl text-gray-300 dark:text-gray-600 mb-4 inline-block"
          />
          <h3 class="text-xl font-semibold mb-2">{{ tooLargeMessage }}</h3>
          <p class="text-gray-600 dark:text-gray-400 mb-6">
            {{
              fileSize > maxPreviewSize
                ? `File is ${formatSize(fileSize)}, too large to preview`
                : "This file type cannot be previewed"
            }}
          </p>
          <el-button type="primary" size="large" @click="downloadFile">
            <div class="i-carbon-download inline-block mr-1" />
            Download File
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import MarkdownViewer from "@/components/common/MarkdownViewer.vue";
import { ElMessage } from "element-plus";

const route = useRoute();
const router = useRouter();

// Route params
const repoType = computed(() => {
  const path = route.path;
  if (path.includes("/models/")) return "model";
  if (path.includes("/datasets/")) return "dataset";
  if (path.includes("/spaces/")) return "space";
  return "model";
});
const namespace = computed(() => route.params.namespace);
const name = computed(() => route.params.name);
const branch = computed(() => route.params.branch || "main");
const filePath = computed(() => route.params.file || "");

// Constants
const maxPreviewSize = 100 * 1024; // 100KB

// State
const loading = ref(true);
const error = ref(null);
const fileContent = ref("");
const fileSize = ref(0);
const fileHeaders = ref({});
const markdownView = ref("preview");

// Computed
const repoTypeLabel = computed(() => {
  const labels = { model: "Models", dataset: "Datasets", space: "Spaces" };
  return labels[repoType.value] || "Models";
});

const fileName = computed(() => {
  const parts = filePath.value.split("/");
  return parts[parts.length - 1] || "unknown";
});

const fileExtension = computed(() => {
  const match = fileName.value.match(/\.([^.]+)$/);
  return match ? match[1].toLowerCase() : "";
});

const pathSegments = computed(() => {
  return filePath.value ? filePath.value.split("/").filter(Boolean) : [];
});

const fileUrl = computed(() => {
  return `/${repoType.value}s/${namespace.value}/${name.value}/resolve/${branch.value}/${filePath.value}`;
});

const languageLabel = computed(() => {
  const langMap = {
    js: "JavaScript",
    ts: "TypeScript",
    py: "Python",
    java: "Java",
    cpp: "C++",
    c: "C",
    cs: "C#",
    go: "Go",
    rs: "Rust",
    rb: "Ruby",
    php: "PHP",
    swift: "Swift",
    kt: "Kotlin",
    scala: "Scala",
    html: "HTML",
    css: "CSS",
    scss: "SCSS",
    json: "JSON",
    xml: "XML",
    yaml: "YAML",
    yml: "YAML",
    toml: "TOML",
    ini: "INI",
    sh: "Shell",
    bash: "Bash",
    sql: "SQL",
    r: "R",
    m: "MATLAB",
    jl: "Julia",
  };
  return langMap[fileExtension.value] || fileExtension.value.toUpperCase();
});

const lineCount = computed(() => {
  return fileContent.value ? fileContent.value.split("\n").length : 0;
});

const isImage = computed(() => {
  return ["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico"].includes(
    fileExtension.value,
  );
});

const isVideo = computed(() => {
  return ["mp4", "webm", "ogg", "mov", "avi"].includes(fileExtension.value);
});

const isAudio = computed(() => {
  return ["mp3", "wav", "ogg", "flac", "m4a", "aac"].includes(
    fileExtension.value,
  );
});

const isPDF = computed(() => {
  return fileExtension.value === "pdf";
});

const isMarkdown = computed(() => {
  return ["md", "markdown"].includes(fileExtension.value);
});

const isTextFile = computed(() => {
  const textExtensions = [
    "txt",
    "log",
    "csv",
    "tsv",
    "js",
    "ts",
    "jsx",
    "tsx",
    "vue",
    "py",
    "java",
    "cpp",
    "c",
    "h",
    "hpp",
    "cs",
    "go",
    "rs",
    "rb",
    "php",
    "swift",
    "kt",
    "scala",
    "m",
    "r",
    "jl",
    "html",
    "htm",
    "css",
    "scss",
    "sass",
    "less",
    "json",
    "xml",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "conf",
    "sh",
    "bash",
    "zsh",
    "fish",
    "ps1",
    "bat",
    "cmd",
    "sql",
    "graphql",
    "proto",
    "dockerfile",
    "makefile",
    "gitignore",
    "env",
    "editorconfig",
    "eslintrc",
    "prettierrc",
  ];
  return (
    textExtensions.includes(fileExtension.value) ||
    fileName.value.toLowerCase().includes("dockerfile")
  );
});

const canPreviewText = computed(() => {
  return (
    isTextFile.value && fileSize.value <= maxPreviewSize && !isMarkdown.value
  );
});

const tooLargeMessage = computed(() => {
  if (fileSize.value > maxPreviewSize && isTextFile.value) {
    return "File Too Large";
  }
  if (isImage.value || isVideo.value || isAudio.value || isPDF.value) {
    return "Media File";
  }
  return "Binary File";
});

// Methods
function getFileIcon(filename) {
  const ext = filename.split(".").pop()?.toLowerCase();

  if (isImage.value) return "i-carbon-image text-purple-500";
  if (isVideo.value) return "i-carbon-video text-red-500";
  if (isAudio.value) return "i-carbon-music text-green-500";
  if (isPDF.value) return "i-carbon-document-pdf text-red-600";
  if (isMarkdown.value) return "i-carbon-logo-markdown text-blue-500";
  if (["js", "ts", "jsx", "tsx"].includes(ext))
    return "i-carbon-code text-yellow-500";
  if (["py"].includes(ext)) return "i-carbon-code text-blue-600";
  if (["json", "xml", "yaml", "yml"].includes(ext))
    return "i-carbon-data-structured text-orange-500";
  if (["zip", "tar", "gz", "rar", "7z"].includes(ext))
    return "i-carbon-zip-archive text-gray-500";

  return "i-carbon-document text-gray-500";
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}

async function loadFileInfo() {
  loading.value = true;
  error.value = null;

  try {
    // First, get file metadata with HEAD request
    const response = await fetch(fileUrl.value, { method: "HEAD" });

    if (!response.ok) {
      throw new Error("File not found");
    }

    fileSize.value = parseInt(response.headers.get("content-length") || "0");
    fileHeaders.value = Object.fromEntries(response.headers.entries());

    // Load content if it's previewable
    if (canPreviewText.value || isMarkdown.value) {
      const contentResponse = await fetch(fileUrl.value);
      fileContent.value = await contentResponse.text();
    }
  } catch (err) {
    error.value = err.message || "Failed to load file";
    console.error("Failed to load file:", err);
  } finally {
    loading.value = false;
  }
}

function downloadFile() {
  window.open(fileUrl.value, "_blank");
}

function copyFileUrl() {
  const fullUrl = window.location.origin + fileUrl.value;
  navigator.clipboard.writeText(fullUrl);
  ElMessage.success("File URL copied to clipboard");
}

function copyContent() {
  navigator.clipboard.writeText(fileContent.value);
  ElMessage.success("Content copied to clipboard");
}

function navigateToFolder(folderPath) {
  // Navigate back to tree viewer with the folder path
  router.push(
    `/${repoType.value}s/${namespace.value}/${name.value}/tree/${branch.value}/${folderPath}`,
  );
}

// Lifecycle
onMounted(() => {
  loadFileInfo();
});
</script>
