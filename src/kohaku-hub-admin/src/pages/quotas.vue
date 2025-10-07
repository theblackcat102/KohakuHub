<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AdminLayout from "@/components/AdminLayout.vue";
import QuotaManager from "@/components/QuotaManager.vue";
import { useAdminStore } from "@/stores/admin";

const route = useRoute();
const router = useRouter();
const adminStore = useAdminStore();

const namespace = ref("");
const isOrg = ref(false);

onMounted(() => {
  if (!adminStore.token) {
    router.push("/login");
    return;
  }

  // Check if namespace is passed via query parameter
  if (route.query.namespace) {
    namespace.value = route.query.namespace;
    isOrg.value = route.query.is_org === "true";
  }
});

watch(
  () => route.query.namespace,
  (newNamespace) => {
    if (newNamespace) {
      namespace.value = newNamespace;
      isOrg.value = route.query.is_org === "true";
    }
  },
);
</script>

<template>
  <AdminLayout>
    <div class="page-container">
      <h1 class="text-3xl font-bold mb-6 text-gray-900 dark:text-gray-100">
        Quota Management
      </h1>

      <el-card class="mb-6">
        <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
          Select Namespace
        </h2>

        <div class="flex gap-4 items-end">
          <el-form-item label="Namespace" class="flex-1">
            <el-input
              v-model="namespace"
              placeholder="Enter username or organization name"
              clearable
            />
          </el-form-item>

          <el-form-item label="Type">
            <el-radio-group v-model="isOrg">
              <el-radio :value="false">User</el-radio>
              <el-radio :value="true">Organization</el-radio>
            </el-radio-group>
          </el-form-item>
        </div>
      </el-card>

      <!-- Quota Manager Component -->
      <QuotaManager
        v-if="namespace && adminStore.token"
        :namespace="namespace"
        :is-org="isOrg"
        :token="adminStore.token"
      />

      <el-empty
        v-else
        description="Enter a namespace to manage quotas"
        :image-size="200"
      />
    </div>
  </AdminLayout>
</template>

<style scoped>
.el-form-item {
  margin-bottom: 0;
}
</style>
