import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueRouter from 'unplugin-vue-router/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  base: '/admin/',
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

  build: {
    // Target modern browsers (skip legacy transpilation)
    target: 'esnext',

    // Enable minification (rolldown uses built-in minifier)
    minify: true,

    // Disable source maps in production (faster builds)
    sourcemap: false,

    // Optimize CSS
    cssMinify: true,

    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Split element-plus into separate chunk
          if (id.includes('element-plus')) {
            return 'element-plus'
          }
          // Split echarts into separate chunk
          if (id.includes('echarts')) {
            return 'echarts'
          }
          // Split core vendor libraries
          if (
            id.includes('node_modules/vue/') ||
            id.includes('node_modules/vue-router/') ||
            id.includes('node_modules/pinia/')
          ) {
            return 'vendor'
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },

  // Enable caching for faster rebuilds
  cacheDir: 'node_modules/.vite',

  server: {
    port: 5174, // Different port from main UI (5173)
    proxy: {
      // Proxy admin API calls
      '/admin/api': {
        target: 'http://localhost:48888',
        changeOrigin: true
      },
      // Proxy standard API calls (for admin token usage)
      '/api': {
        target: 'http://localhost:48888',
        changeOrigin: true
      }
    }
  }
})
