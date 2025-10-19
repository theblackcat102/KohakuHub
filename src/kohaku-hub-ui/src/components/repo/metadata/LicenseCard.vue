<script setup>
import { computed } from "vue";
import {
  getLicenseName,
  getStandardLicenseLink,
} from "@/utils/metadata-helpers";

const props = defineProps({
  metadata: {
    type: Object,
    required: true,
  },
});

const licenseName = computed(() => {
  if (props.metadata.license_name) {
    return props.metadata.license_name;
  }
  return props.metadata.license
    ? getLicenseName(props.metadata.license)
    : "Unknown";
});

const licenseLink = computed(() => {
  if (props.metadata.license_link) {
    return props.metadata.license_link;
  }
  return props.metadata.license
    ? getStandardLicenseLink(props.metadata.license)
    : null;
});
</script>

<template>
  <div class="card">
    <h3 class="font-semibold mb-3 text-gray-900 dark:text-white">License</h3>
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <div
          class="i-carbon-document text-base text-blue-500 dark:text-blue-400"
        />
        <span class="font-medium text-gray-900 dark:text-white">{{
          licenseName
        }}</span>
      </div>
      <a
        v-if="licenseLink"
        :href="licenseLink"
        target="_blank"
        rel="noopener noreferrer"
        class="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
      >
        View License
        <div class="i-carbon-launch text-xs" />
      </a>
    </div>
  </div>
</template>
