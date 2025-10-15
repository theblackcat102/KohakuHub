<!-- src/kohaku-hub-ui/src/pages/register.vue -->
<template>
  <div class="min-h-[calc(100vh-16rem)] flex items-center justify-center">
    <!-- Invitation-only blocked -->
    <div
      v-if="siteConfig?.invitation_only && !invitationToken"
      class="card w-full max-w-md text-center"
    >
      <div class="i-carbon-locked text-6xl text-gray-400 mb-4 inline-block" />
      <h1 class="text-2xl font-bold mb-4">Registration is Invitation-Only</h1>
      <p class="text-gray-600 dark:text-gray-400 mb-6">
        This site requires an invitation to create an account. Please contact
        the administrator for an invitation link.
      </p>
      <el-button type="primary" @click="$router.push('/login')">
        Go to Login
      </el-button>
    </div>

    <!-- Registration form -->
    <div v-else class="card w-full max-w-md">
      <h1 class="text-2xl font-bold mb-6 text-center">Create Account</h1>

      <!-- Invitation info -->
      <div
        v-if="invitationToken"
        class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded"
      >
        <div class="flex items-start gap-2 text-sm">
          <div class="i-carbon-email text-blue-600 text-lg" />
          <div>
            <div class="font-semibold text-blue-800 dark:text-blue-200">
              Using Invitation
            </div>
            <div class="text-blue-700 dark:text-blue-300">
              You're registering with an invitation link
            </div>
          </div>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="Username" prop="username">
          <el-input
            v-model="form.username"
            placeholder="Choose a username"
            size="large"
          />
        </el-form-item>

        <el-form-item label="Email" prop="email">
          <el-input
            v-model="form.email"
            type="email"
            placeholder="your@email.com"
            size="large"
          />
        </el-form-item>

        <el-form-item label="Password" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="Create a password"
            size="large"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="w-full"
          :loading="loading"
          @click="handleSubmit"
        >
          Sign Up
        </el-button>
      </el-form>

      <div class="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
        Already have an account?
        <RouterLink
          to="/login"
          class="text-blue-500 dark:text-blue-400 hover:underline"
        >
          Login
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import axios from "axios";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const formRef = ref(null);
const loading = ref(false);
const siteConfig = ref(null);
const invitationToken = ref(route.query.invitation || null);

const form = reactive({
  username: "",
  email: "",
  password: "",
});

const rules = {
  username: [
    { required: true, message: "Please enter username", trigger: "blur" },
    {
      min: 3,
      message: "Username must be at least 3 characters",
      trigger: "blur",
    },
  ],
  email: [
    { required: true, message: "Please enter email", trigger: "blur" },
    { type: "email", message: "Please enter valid email", trigger: "blur" },
  ],
  password: [
    { required: true, message: "Please enter password", trigger: "blur" },
    {
      min: 6,
      message: "Password must be at least 6 characters",
      trigger: "blur",
    },
  ],
};

async function loadSiteConfig() {
  try {
    const { data } = await axios.get("/api/site-config");
    siteConfig.value = data;

    // If invitation-only and no invitation, user shouldn't be here
    if (data.invitation_only && !invitationToken.value) {
      ElMessage.warning("Registration requires an invitation");
    }
  } catch (err) {
    console.error("Failed to load site config:", err);
  }
}

async function handleSubmit() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    loading.value = true;
    try {
      // Add invitation token to registration if present
      const registerData = { ...form };
      if (invitationToken.value) {
        registerData.invitation_token = invitationToken.value;
      }

      const result = await authStore.register(registerData);
      ElMessage.success(result.message || "Registration successful");

      // Auto login if email verified
      if (result.email_verified) {
        await authStore.login({
          username: form.username,
          password: form.password,
        });

        // Redirect based on context
        const returnUrl = route.query.return;
        if (returnUrl) {
          router.push(decodeURIComponent(returnUrl));
        } else if (invitationToken.value) {
          // If registered with invitation, redirect to home
          router.push("/");
        } else {
          router.push("/");
        }
      } else {
        router.push("/login");
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || "Registration failed");
    } finally {
      loading.value = false;
    }
  });
}

onMounted(() => {
  loadSiteConfig();
});
</script>
