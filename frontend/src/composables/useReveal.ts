import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Scroll-entry reveals for the landing page.
 *
 * Observes every `.lp-reveal` descendant of the given root element and adds
 * `.lp-in` the first time it enters the viewport (threshold 0.18, once).
 * Uses IntersectionObserver — never a scroll listener. Elements with a
 * `data-stagger` attribute cascade through `--i` (see landing.css).
 *
 * When `prefers-reduced-motion` is set, or IntersectionObserver is
 * unavailable, everything is revealed immediately.
 */
export function useReveal(root: () => HTMLElement | null | undefined): void {
  let observer: IntersectionObserver | null = null

  function revealAll() {
    const el = root()
    if (!el) return
    el.querySelectorAll<HTMLElement>('.lp-reveal').forEach((node) => {
      node.classList.add('lp-in')
    })
  }

  onMounted(() => {
    const el = root()
    if (!el) return

    const reduced =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduced || typeof IntersectionObserver === 'undefined') {
      revealAll()
      return
    }

    const nodes = el.querySelectorAll<HTMLElement>('.lp-reveal')
    if (!nodes.length) return

    observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('lp-in')
            observer?.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.18, rootMargin: '0px 0px -6% 0px' },
    )
    nodes.forEach((n) => observer?.observe(n))
  })

  onBeforeUnmount(() => observer?.disconnect())
}
