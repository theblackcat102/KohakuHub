// src/kohaku-hub-ui/src/stores/auth.js
import { defineStore } from 'pinia'
import { authAPI } from '@/utils/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('hf_token') || null,
    loading: false
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.user,
    username: (state) => state.user?.username || null
  },
  
  actions: {
    /**
     * Login user
     * @param {Object} credentials - {username, password}
     */
    async login(credentials) {
      this.loading = true
      try {
        const { data } = await authAPI.login(credentials)
        // Session cookie is set automatically
        await this.fetchUser()
        return data
      } finally {
        this.loading = false
      }
    },
    
    /**
     * Register new user
     * @param {Object} userData - {username, email, password}
     */
    async register(userData) {
      this.loading = true
      try {
        const { data } = await authAPI.register(userData)
        return data
      } finally {
        this.loading = false
      }
    },
    
    /**
     * Logout current user
     */
    async logout() {
      try {
        await authAPI.logout()
      } finally {
        this.user = null
        this.token = null
        localStorage.removeItem('hf_token')
      }
    },
    
    /**
     * Fetch current user info
     */
    async fetchUser() {
      try {
        const { data } = await authAPI.me()
        this.user = data
        return data
      } catch (err) {
        this.user = null
        throw err
      }
    },
    
    /**
     * Set token and fetch user
     * @param {string} token - API token
     */
    async setToken(token) {
      this.token = token
      localStorage.setItem('hf_token', token)
      await this.fetchUser()
    }
  }
})