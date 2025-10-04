<!-- src/pages/organizations/new.vue -->
<template>
  <div class="container-main">
    <div class="max-w-3xl mx-auto">
      <h1 class="text-2xl md:text-3xl font-bold mb-2">
        Create New Organization
      </h1>
      <p
        class="text-sm md:text-base text-gray-600 dark:text-gray-400 mb-6 md:mb-8"
      >
        Organizations allow you to collaborate with others on repositories and
        manage team permissions.
      </p>

      <div class="card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleSubmit"
        >
          <!-- Organization Name -->
          <el-form-item label="Organization Name" prop="name">
            <el-input
              v-model="form.name"
              placeholder="my-organization"
              size="large"
              @input="validateOrgName"
            />
            <div class="text-xs text-gray-500 mt-1">
              <div class="i-carbon-information inline-block mr-1" />
              Only lowercase letters, numbers, and hyphens are allowed
            </div>
          </el-form-item>

          <!-- Description -->
          <el-form-item label="Description" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              placeholder="Describe your organization..."
              size="large"
            />
            <div class="text-xs text-gray-500 mt-1">
              Optional - You can add or update this later
            </div>
          </el-form-item>

          <!-- Submit Buttons -->
          <div class="flex gap-3 mt-6">
            <el-button
              type="primary"
              size="large"
              native-type="submit"
              :loading="creating"
              class="flex-1"
            >
              <div class="i-carbon-add mr-2" />
              Create Organization
            </el-button>
            <el-button size="large" @click="handleCancel">Cancel</el-button>
          </div>
        </el-form>
      </div>

      <!-- Info Section -->
      <div class="mt-8 space-y-4">
        <div class="card bg-blue-50 dark:bg-blue-900/20">
          <div class="flex items-start gap-3">
            <div
              class="i-carbon-information text-2xl text-blue-500 flex-shrink-0"
            />
            <div>
              <h3 class="font-semibold mb-2">About Organizations</h3>
              <ul class="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Create repositories under your organization namespace</li>
                <li>• Add team members with different permission levels</li>
                <li>• Manage access control for all organization repositories</li>
                <li>
                  • Create an organization card by making a
                  <code class="px-1 bg-gray-200 dark:bg-gray-700 rounded"
                    >OrgName/OrgName</code
                  >
                  dataset with a README.md
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { orgAPI } from "@/utils/api";
import { ElMessage } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();

const formRef = ref(null);
const creating = ref(false);
const form = ref({
  name: "",
  description: "",
});

const rules = {
  name: [
    {
      required: true,
      message: "Please enter organization name",
      trigger: "blur",
    },
    {
      pattern: /^[a-z0-9-]+$/,
      message: "Only lowercase letters, numbers, and hyphens allowed",
      trigger: "blur",
    },
    {
      min: 2,
      message: "Name must be at least 2 characters",
      trigger: "blur",
    },
  ],
};

function validateOrgName() {
  form.value.name = form.value.name
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "");
}

function handleCancel() {
  router.push("/organizations");
}

async function handleSubmit() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    creating.value = true;
    try {
      await orgAPI.create({
        name: form.value.name,
        description: form.value.description,
      });

      ElMessage.success("Organization created successfully");

      // Redirect to the new organization page
      router.push(`/organizations/${form.value.name}`);
    } catch (err) {
      console.error("Failed to create organization:", err);
      ElMessage.error(
        err.response?.data?.detail || "Failed to create organization"
      );
    } finally {
      creating.value = false;
    }
  });
}

// Check authentication on mount
onMounted(() => {
  if (!authStore.isAuthenticated) {
    ElMessage.error("You must be logged in to create an organization");
    router.push("/login");
  }
});
</script>
