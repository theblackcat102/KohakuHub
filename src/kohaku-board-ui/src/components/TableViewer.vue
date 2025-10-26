<script setup>
import { useSliderSync } from "@/composables/useSliderSync";

const props = defineProps({
  tableData: Array,
  height: Number,
  currentStep: Number,
  cardId: String,
});

const emit = defineEmits(["update:currentStep"]);

const stepIndex = computed({
  get() {
    if (!props.tableData || props.tableData.length === 0) return 0;
    return props.tableData.findIndex((item) => item.step === props.currentStep);
  },
  set(index) {
    if (props.tableData && props.tableData[index]) {
      const newStep = props.tableData[index].step;
      emit("update:currentStep", newStep);

      // Trigger synchronization if shift is pressed
      triggerSync(newStep);
    }
  },
});

// Setup slider synchronization
const { isShiftPressed, triggerSync } = useSliderSync(
  computed(() => `table-${props.cardId}`),
  computed(() => props.tableData || []),
  (newStep) => {
    emit("update:currentStep", newStep);
  },
);

const experimentId = computed(() => {
  // Extract experiment ID from parent route
  const route = useRoute();
  return route.params.id;
});

const currentTable = computed(() => {
  if (!props.tableData || props.tableData.length === 0) return null;
  const index = stepIndex.value >= 0 ? stepIndex.value : 0;
  return props.tableData[index];
});

const processedTableData = computed(() => {
  if (!currentTable.value) return null;

  // Process table and convert <media id=xxx> to actual URLs
  const tableName = currentTable.value.name.replace("/", "__");
  const step = currentTable.value.step;

  console.log("Processing table:", tableName, "step:", step);
  console.log("Columns:", currentTable.value.columns);
  console.log("Column types:", currentTable.value.column_types);
  console.log("Row count:", currentTable.value.rows.length);
  console.log("First row:", currentTable.value.rows[0]);

  const processedRows = currentTable.value.rows.map((row, rowIdx) => {
    return row.map((cell, colIdx) => {
      const colType = currentTable.value.column_types[colIdx];
      console.log(
        `Row ${rowIdx} Col ${colIdx} type="${colType}" cell:`,
        typeof cell,
        cell.substring ? cell.substring(0, 50) : cell,
      );

      // Check if this column is a media type (image/video/audio)
      if (colType === "media" || colType === "image") {
        // Try multiple patterns for media tags
        if (typeof cell === "string") {
          // Pattern 1: <media id=xxx>
          let match = cell.match(/<media id=([^>]+)>/);
          // Pattern 2: &lt;media id=xxx&gt; (HTML escaped)
          if (!match) {
            match = cell.match(/&lt;media id=([^&]+)&gt;/);
          }

          if (match) {
            const mediaId = match[1];
            const hash8 = mediaId.substring(0, 8);
            const filename = `${tableName}_r${rowIdx}_c${colIdx}_${String(step).padStart(8, "0")}_${hash8}.png`;
            const url = `/api/boards/${experimentId.value}/media/files/${filename}`;
            console.log(`✅ Converted media tag to URL: ${url}`);
            return url;
          } else {
            console.log(`❌ No media tag match for: ${cell.substring(0, 50)}`);
          }
        }
      }
      return cell;
    });
  });

  return {
    ...currentTable.value,
    rows: processedRows,
  };
});
</script>

<template>
  <div class="table-viewer flex flex-col" :style="{ height: `${height}px` }">
    <div v-if="processedTableData" class="flex flex-col h-full">
      <div class="flex-1 overflow-auto relative">
        <!-- Shift indicator -->
        <div
          v-if="isShiftPressed"
          class="absolute top-2 right-2 bg-blue-500 text-white px-2 py-1 rounded text-xs font-bold z-10"
        >
          SYNC MODE
        </div>
        <el-table :data="processedTableData.rows" size="small" stripe>
          <el-table-column
            v-for="(col, idx) in processedTableData.columns"
            :key="idx"
            :prop="String(idx)"
            :label="col"
            :width="
              processedTableData.column_types[idx] === 'image' ? 100 : undefined
            "
          >
            <template #default="{ row }">
              <img
                v-if="
                  processedTableData.column_types[idx] === 'media' ||
                  processedTableData.column_types[idx] === 'image'
                "
                :src="row[idx]"
                class="w-16 h-16 object-cover rounded"
                :alt="`${col} image`"
                @error="
                  (e) => {
                    console.error('Image load error:', row[idx]);
                    e.target.style.display = 'none';
                  }
                "
              />
              <span
                v-else-if="processedTableData.column_types[idx] === 'number'"
              >
                {{
                  typeof row[idx] === "number" ? row[idx].toFixed(3) : row[idx]
                }}
              </span>
              <span v-else>{{ row[idx] }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div class="mt-2 flex justify-center">
        <div class="w-1/2">
          <div
            class="text-sm text-gray-600 dark:text-gray-400 mb-2 text-center"
          >
            Step: {{ processedTableData.step }}
            <span v-if="isShiftPressed" class="text-blue-500 font-bold ml-2">
              (Shift pressed - syncing all sliders)
            </span>
          </div>
          <el-slider
            v-model="stepIndex"
            :min="0"
            :max="tableData.length - 1"
            :marks="{ 0: 'Start', [tableData.length - 1]: 'End' }"
            :format-tooltip="
              (index) => `Step: ${tableData[index]?.step ?? index}`
            "
          />
        </div>
      </div>
    </div>
    <el-empty v-else description="No table data" />
  </div>
</template>
