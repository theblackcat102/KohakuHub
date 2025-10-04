// src/kohaku-hub-ui/src/stores/auth.js
import { defineStore } from "pinia";
import { authAPI, settingsAPI } from "@/utils/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null,
    userOrganizations: [],
    token: localStorage.getItem("hf_token") || null,
    loading: false,
    initialized: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
    username: (state) => state.user?.username || null,
    organizations: (state) => state.userOrganizations,
    organizationNames: (state) =>
      state.userOrganizations.map((org) => org.name),
  },

  actions: {
    /**
     * Login user
     * @param {Object} credentials - {username, password}
     */
    async login(credentials) {
      this.loading = true;
      try {
        const { data } = await authAPI.login(credentials);
        // Session cookie is set automatically
        await this.fetchUserInfo();
        return data;
      } finally {
        this.loading = false;
      }
    },

    /**
     * Register new user
     * @param {Object} userData - {username, email, password}
     */
    async register(userData) {
      this.loading = true;
      try {
        const { data } = await authAPI.register(userData);
        return data;
      } finally {
        this.loading = false;
      }
    },

    /**
     * Logout current user
     */
    async logout() {
      try {
        await authAPI.logout();
      } finally {
        this.user = null;
        this.token = null;
        localStorage.removeItem("hf_token");
      }
    },

    /**
     * Fetch current user info
     */
    async fetchUser() {
      try {
        const { data } = await authAPI.me();
        this.user = data;
        return data;
      } catch (err) {
        this.user = null;
        this.userOrganizations = [];
        throw err;
      }
    },

    /**
     * Fetch user info with organizations
     */
    async fetchUserInfo() {
      try {
        const { data } = await settingsAPI.whoamiV2();
        this.user = {
          username: data.name,
          email: data.email,
          email_verified: data.emailVerified,
          id: data.id,
        };
        this.userOrganizations = data.orgs || [];
        return data;
      } catch (err) {
        this.user = null;
        this.userOrganizations = [];
        throw err;
      }
    },

    /**
     * Set token and fetch user
     * @param {string} token - API token
     */
    async setToken(token) {
      this.token = token;
      localStorage.setItem("hf_token", token);
      await this.fetchUserInfo();
    },

    /**
     * Initialize auth state (restore session on app load)
     */
    async init() {
      if (this.initialized) return;

      this.initialized = true;

      // Try to restore user from session cookie or token
      try {
        await this.fetchUserInfo();
      } catch (err) {
        // Session expired or invalid, clear state
        this.user = null;
        this.userOrganizations = [];
        this.token = null;
        localStorage.removeItem("hf_token");
      }
    },

    /**
     * Check if user has write access to a namespace
     * @param {string} namespace - Namespace to check
     * @returns {boolean}
     */
    canWriteToNamespace(namespace) {
      if (!this.isAuthenticated) return false;
      // Check if it's user's own namespace or an organization they belong to
      return (
        this.username === namespace ||
        this.organizationNames.includes(namespace)
      );
    },
  },
});
