<script setup lang="ts">
import { computed } from 'vue'
import type { SourceStatus } from '@/api/types'

const props = defineProps<{ status: SourceStatus }>()

const label = computed(
  () =>
    ({
      pending: 'Queued',
      fetching: 'Fetching',
      indexing: 'Indexing',
      ready: 'Ready',
      failed: 'Failed',
    })[props.status] ?? props.status,
)
</script>

<template>
  <span class="badge" :class="`badge-${status}`">
    <span v-if="['pending', 'fetching', 'indexing'].includes(status)" class="spinner" />
    {{ label }}
  </span>
</template>
