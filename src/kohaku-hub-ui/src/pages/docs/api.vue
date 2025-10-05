<!-- src/pages/docs/api.vue -->
<script setup>
import { ref, onMounted } from "vue";
import MarkdownPage from "@/components/common/MarkdownPage.vue";

const content = ref("Loading...");
const error = ref(null);

onMounted(async () => {
  try {
    // Fetch the API.md file from the docs directory
    const response = await fetch("/docs/API.md");
    if (!response.ok) {
      throw new Error("Failed to load documentation");
    }
    content.value = await response.text();
  } catch (e) {
    error.value = e.message;
    content.value = `# Error Loading Documentation

${e.message}

Please check the documentation on [GitHub](https://github.com/KohakuBlueleaf/KohakuHub/blob/main/docs/API.md).`;
  }
});
</script>

<template>
  <MarkdownPage :content="content" />
</template>
