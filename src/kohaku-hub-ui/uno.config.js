// src/kohaku-hub-ui/uno.config.js
import { defineConfig, presetAttributify, presetIcons } from 'unocss'
import { presetWind } from '@unocss/preset-wind3'


export default defineConfig({
  presets: [
    presetWind(),
    presetAttributify(),
    presetIcons({
      collections: {
        ep: () => import('@iconify-json/ep/icons.json').then(i => i.default),
        carbon: () => import('@iconify-json/carbon/icons.json').then(i => i.default)
      },
      scale: 1.2,
      warn: true
    })
  ],

  shortcuts: {
    'btn': 'px-4 py-2 rounded cursor-pointer transition-colors',
    'btn-primary': 'btn bg-blue-500 text-white hover:bg-blue-600',
    'btn-secondary': 'btn bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600',
    'card': 'bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4',
    'input': 'px-3 py-2 border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:text-white',
    'container-main': 'max-w-7xl mx-auto px-4 py-6'
  },

  theme: {
    colors: {
      primary: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a'
      }
    }
  }
})