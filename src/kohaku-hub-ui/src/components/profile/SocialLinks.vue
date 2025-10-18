<!-- src/components/profile/SocialLinks.vue -->
<template>
  <div v-if="hasSocialLinks" class="flex gap-3">
    <!-- Icons Column (10% width) -->
    <div class="flex flex-col gap-2 w-10% min-w-8">
      <div
        v-if="socialMedia.twitter_x"
        class="flex items-center justify-center h-6"
      >
        <div class="i-carbon-logo-x w-4 h-4 text-gray-600 dark:text-gray-400" />
      </div>
      <div
        v-if="socialMedia.threads"
        class="flex items-center justify-center h-6"
      >
        <div
          class="i-carbon-logo-instagram w-4 h-4 text-gray-600 dark:text-gray-400"
        />
      </div>
      <div
        v-if="socialMedia.github"
        class="flex items-center justify-center h-6"
      >
        <div
          class="i-carbon-logo-github w-4 h-4 text-gray-600 dark:text-gray-400"
        />
      </div>
      <div
        v-if="socialMedia.huggingface"
        class="flex items-center justify-center h-6"
      >
        <span class="text-base">🤗</span>
      </div>
    </div>

    <!-- Links Column (90% width) -->
    <div class="flex flex-col gap-2 flex-1">
      <a
        v-if="socialMedia.twitter_x"
        :href="`https://twitter.com/${socialMedia.twitter_x}`"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors truncate"
        title="Twitter/X"
      >
        <span v-if="showLabels">@{{ socialMedia.twitter_x }}</span>
        <span v-else>Twitter/X</span>
      </a>

      <a
        v-if="socialMedia.threads"
        :href="`https://www.threads.net/@${socialMedia.threads}`"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors truncate"
        title="Threads"
      >
        <span v-if="showLabels">@{{ socialMedia.threads }}</span>
        <span v-else>Threads</span>
      </a>

      <a
        v-if="socialMedia.github"
        :href="`https://github.com/${socialMedia.github}`"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors truncate"
        title="GitHub"
      >
        <span v-if="showLabels">{{ socialMedia.github }}</span>
        <span v-else>GitHub</span>
      </a>

      <a
        v-if="socialMedia.huggingface"
        :href="`https://huggingface.co/${socialMedia.huggingface}`"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center h-6 text-sm text-gray-700 dark:text-gray-300 hover:text-yellow-600 dark:hover:text-yellow-400 transition-colors truncate"
        title="HuggingFace"
      >
        <span v-if="showLabels">{{ socialMedia.huggingface }}</span>
        <span v-else>HuggingFace</span>
      </a>
    </div>
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
