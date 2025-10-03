<!-- src/pages/about.vue -->
<script setup>
import MarkdownPage from '@/components/common/MarkdownPage.vue'

const content = `# KohakuHub Documents

Coming soon UwU
`
</script>

<template>
  <MarkdownPage :content="content" />
</template>