/** Chart.js setup + pure data/options builders for the usage charts. */
import {
  BarElement,
  CategoryScale,
  Chart,
  Legend,
  LinearScale,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from 'chart.js'

// Concrete colors — the canvas can't resolve CSS variables.
export const PRIMARY = '#4f46e5'
export const OUTPUT = '#10b981'

/** Register the tree-shaken Chart.js pieces (idempotent, safe to call often). */
export function registerChartjs() {
  Chart.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)
}

export interface UsageSeriesPoint {
  date: string
  requests: number
  input_tokens: number
  output_tokens: number
}

/** 1234 -> '1.2k', 2500000 -> '2.5M' (axis + tooltip labels). */
export function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`
  return String(value)
}

function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function barDataset(label: string, data: number[], color: string) {
  return {
    label,
    data,
    backgroundColor: `${color}cc`,
    hoverBackgroundColor: color,
    borderRadius: 5,
    maxBarThickness: 26,
  }
}

/** Requests per day — single indigo dataset. */
export function requestChartData(series: UsageSeriesPoint[]): ChartData<'bar'> {
  return {
    labels: series.map((p) => shortDate(p.date)),
    datasets: [
      barDataset(
        'Requests',
        series.map((p) => p.requests),
        PRIMARY,
      ),
    ],
  }
}

/** Input + Output tokens per day — one stacked bar per day (segments). */
export function tokenChartData(series: UsageSeriesPoint[]): ChartData<'bar'> {
  return {
    labels: series.map((p) => shortDate(p.date)),
    datasets: [
      {
        ...barDataset(
          'Input',
          series.map((p) => p.input_tokens),
          PRIMARY,
        ),
        stack: 'tokens',
      },
      {
        ...barDataset(
          'Output',
          series.map((p) => p.output_tokens),
          OUTPUT,
        ),
        stack: 'tokens',
      },
    ],
  }
}

export function usageChartOptions(labelCount: number, maxValue?: number): ChartOptions<'bar'> {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      // Legend is rendered as HTML outside the canvas (UsageTab) so the plot
      // area is identical across charts and their bars stay level.
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (item) => `${item.dataset.label}: ${formatCompact(item.parsed.y ?? 0)}`,
        },
      },
    },
    scales: {
      x: {
        stacked: true, // tokens chart stacks Input+Output into one bar per day
        grid: { display: false },
        ticks: {
          color: '#8f8a80',
          font: { size: 10 },
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: Math.min(Math.max(labelCount, 1), 9),
        },
      },
      y: {
        beginAtZero: true,
        stacked: true,
        // Fixed axis width: keeps plots horizontally aligned even when tick
        // labels differ in length (e.g. "5" vs "10.0k").
        afterFit: (scale) => {
          scale.width = 44
        },
        // Pin the top to the actual data max so bars fill the plot (no
        // big axis-rounding headroom above them).
        max: maxValue && maxValue > 0 ? maxValue : undefined,
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: {
          color: '#8f8a80',
          font: { size: 10 },
          callback: (value) => formatCompact(Number(value)),
        },
      },
    },
  }
}
