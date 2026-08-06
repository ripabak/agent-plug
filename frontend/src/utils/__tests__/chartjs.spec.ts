import { describe, expect, it } from 'vitest'

import {
  formatCompact,
  requestChartData,
  tokenChartData,
  usageChartOptions,
  type UsageSeriesPoint,
} from '../chartjs'

const SERIES: UsageSeriesPoint[] = [
  { date: '2026-07-06', requests: 1, input_tokens: 100, output_tokens: 50 },
  { date: '2026-07-07', requests: 0, input_tokens: 0, output_tokens: 0 },
  { date: '2026-07-08', requests: 2, input_tokens: 200, output_tokens: 100 },
]

describe('formatCompact', () => {
  it('keeps small numbers as-is', () => {
    expect(formatCompact(0)).toBe('0')
    expect(formatCompact(42)).toBe('42')
    expect(formatCompact(999)).toBe('999')
  })

  it('abbreviates thousands and millions', () => {
    expect(formatCompact(1_000)).toBe('1.0k')
    expect(formatCompact(12_345)).toBe('12.3k')
    expect(formatCompact(2_500_000)).toBe('2.5M')
  })
})

describe('requestChartData', () => {
  it('maps series to a single requests dataset with short date labels', () => {
    const data = requestChartData(SERIES)
    expect(data.datasets).toHaveLength(1)
    expect(data.datasets[0]!.label).toBe('Requests')
    expect(data.datasets[0]!.data).toEqual([1, 0, 2])
    expect(data.labels).toEqual(['Jul 6', 'Jul 7', 'Jul 8'])
  })
})

describe('tokenChartData', () => {
  it('builds input + output datasets that stack into one bar per day', () => {
    const data = tokenChartData(SERIES)
    expect(data.datasets).toHaveLength(2)
    expect(data.datasets.map((d) => d.label)).toEqual(['Input', 'Output'])
    expect(data.datasets[0]!.data).toEqual([100, 0, 200])
    expect(data.datasets[1]!.data).toEqual([50, 0, 100])
    // same stack key → chart.js stacks the two segments per day
    expect(data.datasets[0]!.stack).toBe('tokens')
    expect(data.datasets[1]!.stack).toBe('tokens')
  })

  it('gives the two datasets distinct colors', () => {
    const data = tokenChartData(SERIES)
    expect(data.datasets[0]!.backgroundColor).not.toBe(data.datasets[1]!.backgroundColor)
  })
})

describe('usageChartOptions', () => {
  it('starts the y axis at zero', () => {
    const options = usageChartOptions(3)
    const y = options.scales?.y as { beginAtZero?: boolean } | undefined
    expect(y?.beginAtZero).toBe(true)
  })

  it('keeps the canvas legend hidden (HTML legend renders it instead)', () => {
    expect(usageChartOptions(3).plugins?.legend?.display).toBe(false)
  })

  it('pins the y-axis max to the data max so bars fill the plot', () => {
    const y = usageChartOptions(3, 10300).scales?.y as { max?: number } | undefined
    expect(y?.max).toBe(10300)
    // no maxValue → chart.js picks the axis top itself
    const yDefault = usageChartOptions(3).scales?.y as { max?: number } | undefined
    expect(yDefault?.max).toBeUndefined()
  })

  it('stacks bars on both scales (tokens = Input+Output per day)', () => {
    const options = usageChartOptions(3, 300)
    const x = options.scales?.x as { stacked?: boolean } | undefined
    const y = options.scales?.y as { stacked?: boolean } | undefined
    expect(x?.stacked).toBe(true)
    expect(y?.stacked).toBe(true)
  })

  it('forces a fixed y-axis width for cross-chart alignment', () => {
    const y = usageChartOptions(3, 5).scales?.y as { afterFit?: unknown } | undefined
    expect(typeof y?.afterFit).toBe('function')
  })

  it('thins x labels for long windows', () => {
    expect(usageChartOptions(30).scales?.x?.ticks?.maxTicksLimit).toBe(9)
    expect(usageChartOptions(3).scales?.x?.ticks?.maxTicksLimit).toBe(3)
  })
})
