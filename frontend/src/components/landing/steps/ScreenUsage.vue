<script setup lang="ts">
/**
 * Usage screen — mirrors the dashboard Usage tab (UsageTab.vue): headline
 * request/token stats, a requests-per-day bar chart, and the top-countries
 * list with flags. Used by the landing "Know who's asking" section as an ad
 * for the usage analytics feature. Static mock, aria-hidden.
 */
import { countryFlag, countryName } from '@/utils/country'

const stats = [
  { label: 'Requests', value: '1,284' },
  { label: 'Input', value: '2.4M' },
  { label: 'Output', value: '1.1M' },
]

/** Requests per day (arbitrary heights, %, drives the chart bars). */
const days = [12, 18, 9, 21, 15, 26, 19, 30, 22, 17, 28, 24, 31, 27, 20, 33, 25, 18, 29, 23]

const countries = [
  { code: 'ID', n: 412, pct: 32 },
  { code: 'US', n: 268, pct: 21 },
  { code: 'SG', n: 147, pct: 11 },
  { code: 'DE', n: 96, pct: 7 },
]
</script>

<template>
  <div class="lp-win lp-usage-win" aria-hidden="true">
    <div class="lp-win-bar">
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-dot" />
      <span class="lp-win-title">Usage</span>
      <span class="lp-win-spacer" />
    </div>
    <div class="lp-win-body">
      <div class="lp-usage-stats">
        <div v-for="s in stats" :key="s.label" class="lp-usage-stat">
          <div class="lp-usage-stat-num">{{ s.value }}</div>
          <div class="lp-usage-stat-label">{{ s.label }}</div>
        </div>
      </div>

      <div class="lp-usage-chart">
        <div v-for="(d, i) in days" :key="i" class="lp-usage-bar" :style="{ height: d + '%' }" />
      </div>

      <p class="lp-usage-sub">Top countries</p>
      <ol class="lp-usage-countries">
        <li v-for="c in countries" :key="c.code" class="lp-usage-country">
          <span class="lp-usage-flag">{{ countryFlag(c.code) }}</span>
          <span class="lp-usage-cname">{{ countryName(c.code) }}</span>
          <span class="lp-usage-cbar">
            <span class="lp-usage-cfill" :style="{ width: c.pct + '%' }" />
          </span>
          <span class="lp-usage-cnum">{{ c.n }}</span>
        </li>
      </ol>
    </div>
  </div>
</template>
