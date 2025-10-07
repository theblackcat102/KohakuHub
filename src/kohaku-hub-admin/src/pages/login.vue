<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAdminStore } from "@/stores/admin";
import { ElMessage } from "element-plus";

const router = useRouter();
const adminStore = useAdminStore();

const tokenInput = ref("");
const loading = ref(false);

async function handleLogin() {
  if (!tokenInput.value) {
    ElMessage.error("Please enter admin token");
    return;
  }

  loading.value = true;

  try {
    const success = await adminStore.login(tokenInput.value);
    if (success) {
      ElMessage.success("Login successful");
      router.push("/");
    } else {
      ElMessage.error("Invalid admin token");
      tokenInput.value = "";
    }
  } catch (error) {
    console.error("Login error:", error);
    ElMessage.error(error.response?.data?.detail?.error || "Login failed");
    tokenInput.value = "";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="i-carbon-security text-4xl text-blue-600 dark:text-blue-400 mb-4" />
        <h1 class="text-3xl font-bold mb-2 text-gray-900 dark:text-gray-100">KohakuHub Admin</h1>
        <p class="text-gray-600 dark:text-gray-400">
          Enter your admin token to continue
        </p>
      </div>

      <el-form @submit.prevent="handleLogin" class="login-form">
        <el-form-item>
          <el-input
            v-model="tokenInput"
            type="password"
            placeholder="Admin Token"
            size="large"
            :prefix-icon="'Lock'"
            show-password
            autocomplete="off"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          native-type="submit"
          class="w-full"
        >
          {{ loading ? "Verifying..." : "Login" }}
        </el-button>
      </el-form>

      <div class="login-footer">
        <el-alert type="info" :closable="false" show-icon>
          <p class="text-sm">
            Admin token can be found in your environment configuration:
            <code class="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
              KOHAKU_HUB_ADMIN_SECRET_TOKEN
            </code>
          </p>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 40px;
  width: 100%;
  max-width: 450px;
}

html.dark .login-card {
  background: #1f1f1f;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-form {
  margin-bottom: 24px;
}

.login-footer {
  margin-top: 24px;
}

code {
  font-family: "Courier New", monospace;
  font-size: 12px;
}
</style>
