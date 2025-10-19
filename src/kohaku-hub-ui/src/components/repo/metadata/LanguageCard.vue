<script setup>
import { computed } from "vue";
import { getLanguageName } from "@/utils/metadata-helpers";

const props = defineProps({
  languages: {
    type: Array,
    required: true,
  },
});

const languageList = computed(() => {
  if (!props.languages || !Array.isArray(props.languages)) return [];
  return props.languages.map((code) => ({
    code,
    name: getLanguageName(code),
  }));
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">
      Language{{ languageList.length > 1 ? "s" : "" }}
    </h3>
    <div class="flex flex-wrap gap-2">
      <el-tag
        v-for="lang in languageList"
        :key="lang.code"
        size="small"
        type="info"
      >
        <div class="i-carbon-language inline-block mr-1" />
        {{ lang.name }}
      </el-tag>
    </div>
  </div>
</template>
