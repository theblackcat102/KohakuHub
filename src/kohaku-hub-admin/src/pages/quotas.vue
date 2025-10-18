<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAdminStore } from "@/stores/admin";

const router = useRouter();
const adminStore = useAdminStore();

onMounted(() => {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  // Redirect to new Quota Overview page
  router.push("/QuotaOverview");
});
</script>

<template>
  <div class="redirect-page">
    <p>Redirecting to Quota Overview...</p>
  </div>
</template>

<style scoped>
.redirect-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 18px;
  color: #606266;
}
</style>
