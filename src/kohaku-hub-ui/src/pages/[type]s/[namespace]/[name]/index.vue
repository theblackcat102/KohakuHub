<!-- src/kohaku-hub-ui/src/pages/[type]s/[namespace]/[name]/index.vue -->
<template>
  <RepoViewer
    :repo-type="repoType"
    :namespace="namespace"
    :name="name"
    tab="card"
  />
</template>

<script setup>
import RepoViewer from "@/components/repo/RepoViewer.vue";

const route = useRoute();

const repoType = computed(() => {
  const path = route.path;
  if (path.includes("/models/")) return "model";
  if (path.includes("/datasets/")) return "dataset";
  if (path.includes("/spaces/")) return "space";
  return "model";
});

const namespace = computed(() => route.params.namespace);
const name = computed(() => route.params.name);
</script>
