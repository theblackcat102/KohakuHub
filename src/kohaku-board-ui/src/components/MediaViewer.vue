<script setup>
const props = defineProps({
  mediaData: Array,
  height: Number,
  currentStep: Number,
});

const emit = defineEmits(["update:currentStep"]);

const stepIndex = computed({
  get() {
    if (!props.mediaData || props.mediaData.length === 0) return 0;
    return props.mediaData.findIndex((item) => item.step === props.currentStep);
  },
  set(index) {
    if (props.mediaData && props.mediaData[index]) {
      emit("update:currentStep", props.mediaData[index].step);
    }
  },
});

const currentMedia = computed(() => {
  if (!props.mediaData || props.mediaData.length === 0) return null;
  const index = stepIndex.value >= 0 ? stepIndex.value : 0;
  return props.mediaData[index];
});
</script>

<template>
  <div class="media-viewer flex flex-col" :style="{ height: `${height}px` }">
    <div v-if="currentMedia" class="flex flex-col h-full">
      <div
        class="flex-1 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded overflow-hidden"
      >
        <img
          v-if="currentMedia.type === 'image'"
          :src="currentMedia.url"
          :alt="currentMedia.caption"
          class="max-w-full max-h-full object-contain"
        />
        <video
          v-else-if="currentMedia.type === 'video'"
          :src="currentMedia.url"
          controls
          class="max-w-full max-h-full"
        />
      </div>
      <div class="mt-2 flex justify-center">
        <div class="w-1/2">
          <div
            class="text-sm text-gray-600 dark:text-gray-400 mb-2 text-center"
          >
            {{ currentMedia.caption }} - Step: {{ currentMedia.step }}
          </div>
          <el-slider
            v-model="stepIndex"
            :min="0"
            :max="mediaData.length - 1"
            :marks="{ 0: 'Start', [mediaData.length - 1]: 'End' }"
          />
        </div>
      </div>
    </div>
    <el-empty v-else description="No media data" />
  </div>
</template>

<style scoped>
.media-viewer {
  display: flex;
  flex-direction: column;
}
</style>
