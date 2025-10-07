import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { verifyAdminToken } from "@/utils/api";

/**
 * Admin store - manages admin token in memory only (no persistence)
 */
export const useAdminStore = defineStore("admin", () => {
  // State - token is kept in memory only, not persisted
  const token = ref("");
  const isAuthenticated = ref(false);

  // Computed
  const hasToken = computed(() => !!token.value);

  // Actions
  async function login(adminToken) {
    // Verify token is valid before storing
    try {
      const valid = await verifyAdminToken(adminToken);
      if (valid) {
        token.value = adminToken;
        isAuthenticated.value = true;
        return true;
      } else {
        token.value = "";
        isAuthenticated.value = false;
        return false;
      }
    } catch (error) {
      token.value = "";
      isAuthenticated.value = false;
      throw error;
    }
  }

  function logout() {
    token.value = "";
    isAuthenticated.value = false;
  }

  return {
    token,
    isAuthenticated,
    hasToken,
    login,
    logout,
  };
});
