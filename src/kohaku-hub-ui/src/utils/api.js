// src/kohaku-hub-ui/src/utils/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true
})

// Request interceptor
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('hf_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => response,
  error => {
    // Don't auto-redirect on 401, let components handle it
    // This allows visitors to browse public content without login
    return Promise.reject(error)
  }
)

export default api

/**
 * Auth API
 */
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  createToken: (data) => api.post('/auth/tokens/create', data),
  listTokens: () => api.get('/auth/tokens'),
  revokeToken: (id) => api.delete(`/auth/tokens/${id}`)
}

/**
 * Repo API
 * Backend expects:
 * - create: { type, name, organization, private, sdk? }
 * - delete: { type, name, organization?, sdk? }
 */
export const repoAPI = {
  /**
   * Create a new repository
   * @param {Object} data - { type: string, name: string, organization: string|null, private: boolean }
   * @returns {Promise} - { url: string, repo_id: string }
   */
  create: (data) => api.post('/repos/create', data),
  
  /**
   * Delete a repository
   * @param {Object} data - { type: string, name: string, organization?: string }
   * @returns {Promise} - { message: string }
   */
  delete: (data) => api.delete('/repos/delete', { data }),
  
  /**
   * Get repository info
   * @param {string} type - Repository type (model/dataset/space)
   * @param {string} namespace - Owner namespace
   * @param {string} name - Repository name
   * @returns {Promise} - Repository metadata
   */
  getInfo: (type, namespace, name) => api.get(`/${type}s/${namespace}/${name}`),
  
  /**
   * List repositories
   * @param {string} type - Repository type (model/dataset/space)
   * @param {Object} params - Query parameters { author?, limit? }
   * @returns {Promise} - Array of repositories
   */
  listRepos: (type, params) => api.get(`/${type}s`, { params }),
  
  /**
   * List repository file tree
   * @param {string} type - Repository type
   * @param {string} namespace - Owner namespace
   * @param {string} name - Repository name
   * @param {string} revision - Branch name or commit hash
   * @param {string} path - Path within repository (with leading /)
   * @param {Object} params - Query parameters { recursive?, expand? }
   * @returns {Promise} - Array of files and directories
   */
  listTree: (type, namespace, name, revision, path, params) => 
    api.get(`/${type}s/${namespace}/${name}/tree/${revision}${path}`, { params })
}

/**
 * Organization API
 */
export const orgAPI = {
  /**
   * Create a new organization
   * @param {Object} data - { name: string, description?: string }
   * @returns {Promise} - { success: boolean, name: string }
   */
  create: (data) => api.post('/org/create', data),
  
  /**
   * Get organization details
   * @param {string} name - Organization name
   * @returns {Promise} - { name, description, created_at }
   */
  get: (name) => api.get(`/org/${name}`),
  
  /**
   * Add member to organization
   * @param {string} name - Organization name
   * @param {Object} data - { username: string, role: string }
   * @returns {Promise} - { success: boolean, message: string }
   */
  addMember: (name, data) => api.post(`/org/${name}/members`, data),
  
  /**
   * Remove member from organization
   * @param {string} name - Organization name
   * @param {string} username - Username to remove
   * @returns {Promise} - { success: boolean, message: string }
   */
  removeMember: (name, username) => api.delete(`/org/${name}/members/${username}`),
  
  /**
   * Update member role
   * @param {string} name - Organization name
   * @param {string} username - Username to update
   * @param {Object} data - { role: string }
   * @returns {Promise} - { success: boolean, message: string }
   */
  updateMemberRole: (name, username, data) => api.put(`/org/${name}/members/${username}`, data),
  
  /**
   * Get user's organizations
   * @param {string} username - Username
   * @returns {Promise} - { organizations: Array<{ name, description, role }> }
   */
  getUserOrgs: (username) => api.get(`/org/users/${username}/orgs`)
}