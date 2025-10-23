# Dataset Viewer - Frontend Components

Vue 3 components for previewing dataset files.

## Components

### DatasetViewer.vue

Main container component that handles loading and displaying dataset previews.

**Props:**
- `fileUrl` (String, required): S3 presigned URL or HTTP(S) URL
- `fileName` (String, required): File name (for format detection)
- `maxRows` (Number, default: 1000): Maximum rows to display

**Events:**
- `@error`: Emitted when an error occurs

**Example:**
```vue
<script setup>
import DatasetViewer from '@/components/DatasetViewer/DatasetViewer.vue'

const fileUrl = 'https://s3.amazonaws.com/bucket/data.csv?X-Amz-...'
</script>

<template>
  <DatasetViewer
    :file-url="fileUrl"
    :file-name="data.csv"
    :max-rows="1000"
    @error="handleError"
  />
</template>
```

### DataGrid.vue

Tabular data display with sorting.

**Props:**
- `columns` (Array, required): Column names
- `rows` (Array, required): Row data (2D array)
- `truncated` (Boolean): Whether data is truncated

**Features:**
- Click column headers to sort
- Ascending/descending toggle
- Max height: 600px (scrollable)
- Max cell width: 300px (ellipsis)

### TARFileList.vue

File browser for TAR archives.

**Props:**
- `files` (Array, required): File list from backend

**Events:**
- `@select`: Emitted when user selects a file

**Features:**
- Grouped by directory
- Search/filter
- Shows file sizes
- Only previewable files are clickable

## API Client (api.js)

```javascript
import {
  previewFile,
  listTARFiles,
  extractTARFile,
  getRateLimitStats,
  detectFormat,
  formatBytes
} from '@/components/DatasetViewer/api'
```

### previewFile(url, options)

Preview a dataset file.

**Arguments:**
- `url` (String): File URL
- `options` (Object):
  - `format` (String): File format (auto-detect if omitted)
  - `maxRows` (Number): Max rows to return
  - `delimiter` (String): CSV delimiter

**Returns:** Promise<Object>
```javascript
{
  columns: ['col1', 'col2'],
  rows: [['val1', 'val2']],
  total_rows: 1,
  truncated: false,
  file_size: 1024,
  format: 'csv'
}
```

### listTARFiles(url)

List files in TAR archive.

**Returns:** Promise<Object>
```javascript
{
  files: [
    { name: 'train.csv', size: 10240, offset: 512 }
  ],
  total_size: 20480
}
```

### extractTARFile(url, fileName)

Extract file from TAR archive.

**Returns:** Promise<Blob>

### getRateLimitStats()

Get rate limit statistics.

**Returns:** Promise<Object>
```javascript
{
  requests_used: 10,
  requests_limit: 60,
  concurrent_requests: 1,
  concurrent_limit: 3,
  bytes_processed: 1048576,
  window_seconds: 60
}
```

### detectFormat(filename)

Detect file format from filename.

**Returns:** String | null

Supported formats: `csv`, `tsv`, `json`, `jsonl`, `parquet`, `tar`

### formatBytes(bytes)

Format bytes to human-readable string.

**Returns:** String (e.g., "1.5 MB")

## Usage Example

### Basic Preview

```vue
<script setup>
import { ref } from 'vue'
import DatasetViewer from '@/components/DatasetViewer/DatasetViewer.vue'
import { repoAPI } from '@/utils/api'

const props = defineProps(['namespace', 'name', 'path'])

// Get presigned URL from KohakuHub API
const fileUrl = ref(null)

async function loadFile() {
  const response = await repoAPI.downloadFile(
    'dataset',
    props.namespace,
    props.name,
    'main',
    props.path
  )
  fileUrl.value = response.request.responseURL  // Follow redirect to get presigned URL
}

loadFile()
</script>

<template>
  <div v-if="fileUrl">
    <DatasetViewer
      :file-url="fileUrl"
      :file-name="path"
      :max-rows="1000"
    />
  </div>
</template>
```

### Integrated into Repo Viewer

```vue
<!-- In pages/[type]s/[namespace]/[name]/index.vue -->
<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import DatasetViewer from '@/components/DatasetViewer/DatasetViewer.vue'
import { repoAPI } from '@/utils/api'

const route = useRoute()
const selectedFile = ref(null)

// Get presigned URL for file
async function previewFile(file) {
  const url = `/${route.params.type}s/${route.params.namespace}/${route.params.name}/resolve/main/${file.path}`
  const response = await fetch(url, { method: 'HEAD' })
  selectedFile.value = {
    name: file.path,
    url: response.url
  }
}
</script>

<template>
  <div class="repo-viewer">
    <!-- File tree -->
    <div class="file-tree">
      <div
        v-for="file in files"
        :key="file.path"
        @click="previewFile(file)"
      >
        {{ file.path }}
      </div>
    </div>

    <!-- Dataset viewer -->
    <div v-if="selectedFile" class="preview">
      <DatasetViewer
        :file-url="selectedFile.url"
        :file-name="selectedFile.name"
      />
    </div>
  </div>
</template>
```

## Styling

All components support dark mode out of the box:
```vue
<div class="bg-white dark:bg-gray-900 text-black dark:text-white">
```

Customize with CSS:
```css
.dataset-viewer {
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.data-grid-container {
  max-height: 800px;  /* Increase max height */
}
```

## Error Handling

```vue
<script setup>
import { ref } from 'vue'

const error = ref(null)

function handleError(err) {
  error.value = err
  console.error('Dataset viewer error:', err)

  // Show notification
  ElMessage.error({
    message: `Failed to load preview: ${err}`,
    duration: 5000
  })
}
</script>

<template>
  <DatasetViewer
    :file-url="url"
    :file-name="name"
    @error="handleError"
  />

  <div v-if="error" class="error-banner">
    {{ error }}
  </div>
</template>
```

## Performance Tips

1. **Limit max_rows**: Default 1000 is good balance
2. **Lazy load**: Only render viewer when file is selected
3. **Cancel requests**: Use AbortController for navigation
4. **Cache URLs**: Reuse presigned URLs (valid for 1 hour)

## Browser Compatibility

- Chrome: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Edge: ✅ Full support

Requires modern browser with fetch() and async/await support.

## License

MIT License - Free for commercial and non-commercial use.

---

**Questions?** Check the backend README or open an issue!
