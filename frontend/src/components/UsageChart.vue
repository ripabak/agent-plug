<script setup lang="ts">
import { computed } from 'vue'
import type { ChartData, ChartOptions } from 'chart.js'
import { Bar } from 'vue-chartjs'

import { registerChartjs, usageChartOptions } from '@/utils/chartjs'

registerChartjs()

const props = defineProps<{ data: ChartData<'bar'> }>()

/**
 * Highest TOTAL bar height across categories (sum of all datasets per index).
 * For stacked bars (tokens) this is Input+Output per day; for a single
 * dataset (requests) it's just the value — pins the y-axis top so bars fill
 * the plot without headroom.
 */
const maxValue = computed(() => {
  const datasets = props.data.datasets ?? []
  const len = Math.max(0, ...datasets.map((d) => (Array.isArray(d.data) ? d.data.length : 0)))
  let max = 0
  for (let i = 0; i < len; i++) {
    let sum = 0
    for (const d of datasets) {
      const v = Array.isArray(d.data) ? d.data[i] : 0
      if (typeof v === 'number') sum += v
    }
    max = Math.max(max, sum)
  }
  return max
})

const options = computed<ChartOptions<'bar'>>(() =>
  usageChartOptions(props.data.labels?.length ?? 0, maxValue.value),
)
</script>

<template>
  <div class="usage-chart-box">
    <Bar :data="data" :options="options" />
  </div>
</template>
