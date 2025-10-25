<script setup>
const props = defineProps({
  tableData: Array,
  height: Number,
  currentStep: Number,
});

const emit = defineEmits(["update:currentStep"]);

const stepIndex = computed({
  get() {
    if (!props.tableData || props.tableData.length === 0) return 0;
    return props.tableData.findIndex((item) => item.step === props.currentStep);
  },
  set(index) {
    if (props.tableData && props.tableData[index]) {
      emit("update:currentStep", props.tableData[index].step);
    }
  },
});

const currentTable = computed(() => {
  if (!props.tableData || props.tableData.length === 0) return null;
  const index = stepIndex.value >= 0 ? stepIndex.value : 0;
  return props.tableData[index];
});
</script>

<template>
  <div class="table-viewer flex flex-col" :style="{ height: `${height}px` }">
    <div v-if="currentTable" class="flex flex-col h-full">
      <div class="flex-1 overflow-auto">
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
          </div>
          <el-slider
            v-model="stepIndex"
            :min="0"
            :max="tableData.length - 1"
            :marks="{ 0: 'Start', [tableData.length - 1]: 'End' }"
          />
        </div>
      </div>
    </div>
    <el-empty v-else description="No table data" />
  </div>
</template>
