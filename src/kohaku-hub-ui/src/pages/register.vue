<!-- src/kohaku-hub-ui/src/pages/register.vue -->
<template>
  <div class="min-h-[calc(100vh-16rem)] flex items-center justify-center">
    <div class="card w-full max-w-md">
      <h1 class="text-2xl font-bold mb-6 text-center">Create Account</h1>

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
import { ElMessage } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();
const formRef = ref(null);
const loading = ref(false);

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

async function handleSubmit() {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (!valid) return;

    loading.value = true;
    try {
      const result = await authStore.register(form);
      ElMessage.success(result.message || "Registration successful");

      // Auto login if email verified
      if (result.email_verified) {
        await authStore.login({
          username: form.username,
          password: form.password,
        });
        router.push("/");
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
</script>
