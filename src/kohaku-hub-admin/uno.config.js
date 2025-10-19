import { defineConfig, presetAttributify, presetIcons, presetUno } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
    presetIcons({
      scale: 1.2,
      warn: false,  // Disable warnings for missing icons (false positives)
      collections: {
        carbon: () =>
          import('@iconify-json/carbon/icons.json', { with: { type: 'json' } }).then(
            (i) => i.default
          ),
        ep: () =>
          import('@iconify-json/ep/icons.json', { with: { type: 'json' } }).then((i) => i.default)
      }
    })
  ],
  safelist: [
    // Explicitly safelist icons used in dynamic contexts
    'i-carbon-user',
    'i-carbon-data-base',
    'i-carbon-version',
    'i-carbon-search',
    'i-carbon-circle-dash',
    'i-carbon-search-locate',
  ],
  shortcuts: {
    'btn-primary':
      'px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
    'btn-secondary':
      'px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 cursor-pointer',
    'btn-danger':
      'px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
    'card': 'bg-white dark:bg-gray-800 rounded-lg shadow p-6',
    'input-field':
      'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100',
    'page-container': 'max-w-7xl mx-auto px-4 py-8',
    'stat-card': 'bg-gradient-to-br p-6 rounded-lg shadow text-white'
  },
  theme: {
    colors: {
      primary: '#409EFF'
    }
  }
})
