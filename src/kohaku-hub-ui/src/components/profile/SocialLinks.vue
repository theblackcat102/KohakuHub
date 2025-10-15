<!-- src/components/profile/SocialLinks.vue -->
<template>
  <div v-if="hasSocialLinks" class="flex flex-wrap gap-2">
    <a
      v-if="socialMedia.twitter_x"
      :href="`https://twitter.com/${socialMedia.twitter_x}`"
      target="_blank"
      rel="noopener noreferrer"
      class="inline-flex items-center gap-1 px-2 py-1 text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
      title="Twitter/X"
    >
      <div class="i-carbon-logo-x w-4 h-4" />
      <span v-if="showLabels">@{{ socialMedia.twitter_x }}</span>
    </a>

    <a
      v-if="socialMedia.threads"
      :href="`https://www.threads.net/@${socialMedia.threads}`"
      target="_blank"
      rel="noopener noreferrer"
      class="inline-flex items-center gap-1 px-2 py-1 text-sm text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
      title="Threads"
    >
      <div class="i-carbon-logo-instagram w-4 h-4" />
      <span v-if="showLabels">@{{ socialMedia.threads }}</span>
    </a>

    <a
      v-if="socialMedia.github"
      :href="`https://github.com/${socialMedia.github}`"
      target="_blank"
      rel="noopener noreferrer"
      class="inline-flex items-center gap-1 px-2 py-1 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
      title="GitHub"
    >
      <div class="i-carbon-logo-github w-4 h-4" />
      <span v-if="showLabels">{{ socialMedia.github }}</span>
    </a>

    <a
      v-if="socialMedia.huggingface"
      :href="`https://huggingface.co/${socialMedia.huggingface}`"
      target="_blank"
      rel="noopener noreferrer"
      class="inline-flex items-center gap-1 px-2 py-1 text-sm text-gray-700 dark:text-gray-300 hover:text-yellow-600 dark:hover:text-yellow-400 transition-colors"
      title="HuggingFace"
    >
      <span class="text-base">🤗</span>
      <span v-if="showLabels">{{ socialMedia.huggingface }}</span>
    </a>
  </div>
</template>

<script setup>
const props = defineProps({
  socialMedia: {
    type: Object,
    default: () => ({}),
  },
  showLabels: {
    type: Boolean,
    default: true,
  },
});

const hasSocialLinks = computed(() => {
  if (!props.socialMedia) return false;
  return (
    props.socialMedia.twitter_x ||
    props.socialMedia.threads ||
    props.socialMedia.github ||
    props.socialMedia.huggingface
  );
});
</script>
