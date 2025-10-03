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
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('hf_token')
      window.location.href = '/login'
    }
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
 */
export const repoAPI = {
  create: (data) => api.post('/repos/create', data),
  delete: (data) => api.delete('/repos/delete', { data }),
  getInfo: (type, namespace, name) => api.get(`/${type}s/${namespace}/${name}`),
  listRepos: (type, params) => api.get(`/${type}s`, { params }),
  listTree: (type, namespace, name, revision, path, params) => 
    api.get(`/${type}s/${namespace}/${name}/tree/${revision}${path}`, { params })
}

/**
 * Organization API
 */
export const orgAPI = {
  create: (data) => api.post('/org/create', data),
  get: (name) => api.get(`/org/${name}`),
  addMember: (name, data) => api.post(`/org/${name}/members`, data),
  removeMember: (name, username) => api.delete(`/org/${name}/members/${username}`),
  updateMemberRole: (name, username, data) => api.put(`/org/${name}/members/${username}`, data),
  getUserOrgs: (username) => api.get(`/org/users/${username}/orgs`)
}