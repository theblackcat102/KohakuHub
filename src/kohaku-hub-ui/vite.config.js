// src/kohaku-hub-ui/vite.config.js
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueRouter from 'unplugin-vue-router/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  plugins: [
    // Must be before Vue plugin
    VueRouter({
      routesFolder: 'src/pages',
      dts: 'src/typed-router.d.ts',
      extensions: ['.vue'],
      exclude: ['**/components/**']
    }),
    
    vue(),
    
    // Auto import APIs
    AutoImport({
      imports: [
        'vue',
        'pinia',
        'vue-router',
        {
          'vue-router/auto': ['useRoute', 'useRouter']
        }
      ],
      resolvers: [ElementPlusResolver()],
      dts: 'src/auto-imports.d.ts',
      eslintrc: {
        enabled: true
      }
    }),
    
    // Auto import components
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
      dirs: ['src/components']
    }),
    
    UnoCSS()
  ],
  
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls
      '/api': {
        target: 'http://localhost:48888',
        changeOrigin: true
      },
      // Proxy organization endpoints
      '/org': {
        target: 'http://localhost:48888',
        changeOrigin: true
      },
      // Proxy file resolve/download endpoints (models/datasets/spaces)
      // This catches: /models/*/resolve/*, /datasets/*/resolve/*, /spaces/*/resolve/*
      '^/(models|datasets|spaces)/.+/resolve/': {
        target: 'http://localhost:48888',
        changeOrigin: true
      },
      // Proxy direct download endpoints (for backward compatibility)
      // This catches: /namespace/name/resolve/*
      '^/[^/]+/[^/]+/resolve/': {
        target: 'http://localhost:48888',
        changeOrigin: true
      }
    }
  }
})