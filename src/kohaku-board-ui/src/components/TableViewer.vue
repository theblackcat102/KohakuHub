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

const currentTable = computed(() => {
  if (!props.tableData || props.tableData.length === 0) return null;
  const index = stepIndex.value >= 0 ? stepIndex.value : 0;
  return props.tableData[index];
});
</script>

<template>
  <div class="table-viewer flex flex-col" :style="{ height: `${height}px` }">
    <div v-if="currentTable" class="flex flex-col h-full">
      <div class="flex-1 overflow-auto relative">
        <!-- Shift indicator -->
        <div
          v-if="isShiftPressed"
          class="absolute top-2 right-2 bg-blue-500 text-white px-2 py-1 rounded text-xs font-bold z-10"
        >
          SYNC MODE
        </div>
        <el-table :data="currentTable.rows" size="small" stripe>
          <el-table-column
            v-for="(col, idx) in currentTable.columns"
            :key="idx"
            :prop="String(idx)"
            :label="col"
            :width="
              currentTable.column_types[idx] === 'image' ? 100 : undefined
            "
          >
            <template #default="{ row }">
              <img
                v-if="currentTable.column_types[idx] === 'image'"
                :src="row[idx]"
                class="w-16 h-16 object-cover rounded"
                :alt="`${col} image`"
              />
              <span v-else-if="currentTable.column_types[idx] === 'number'">
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
            Step: {{ currentTable.step }}
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
