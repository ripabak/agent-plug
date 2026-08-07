<script setup lang="ts">
/**
 * LandingView — the public marketing page for Agent-Plug.
 *
 * Narrative (scroll story): the problem (curious visitors leave too soon) →
 * statistics → the fix (an agent that already knows your business) → a
 * five-screen tour of the real dashboard (create, teach, style, publish,
 * done) → FAQ → CTA.
 *
 * Copy is deliberately non-technical: it speaks about visitor experience
 * (staying longer, understanding the business), never about the stack.
 *
 * Aesthetic: warm monochrome editorial (minimalist-ui protocol). Brand mark:
 * the "plug" (brandkit): chat bubble + socket slots = "add a friendly agent
 * to your website". All motion is IntersectionObserver-driven;
 * prefers-reduced-motion degrades to static.
 */
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

import '@/assets/landing.css'

import PlugMark from '@/components/PlugMark.vue'
import WidgetMock from '@/components/landing/WidgetMock.vue'
import LandingFaq from '@/components/landing/LandingFaq.vue'
import ScreenUsage from '@/components/landing/steps/ScreenUsage.vue'
import ScreenCreate from '@/components/landing/steps/ScreenCreate.vue'
import ScreenKnowledge from '@/components/landing/steps/ScreenKnowledge.vue'
import ScreenTheme from '@/components/landing/steps/ScreenTheme.vue'
import ScreenEmbed from '@/components/landing/steps/ScreenEmbed.vue'
import ScreenLive from '@/components/landing/steps/ScreenLive.vue'
import { useReveal } from '@/composables/useReveal'

const auth = useAuthStore()
const authed = computed(() => auth.isAuthenticated)

/** Marketing slogan — shown in the footer + closing CTA. Swap here to test. */
const SLOGAN = "Visitors stay. Questions don't."

const rootEl = ref<HTMLElement | null>(null)
useReveal(() => rootEl.value)

const steps = [
  {
    verb: 'Create',
    title: 'Give your agent a name.',
    body: 'A name, a short greeting, a friendly face. It quickly starts to feel like part of your team.',
    time: '≈ 30 seconds',
    screen: ScreenCreate,
  },
  {
    verb: 'Teach',
    title: 'Tell it about your business.',
    body: 'Add the pages of your website, a document, or a few notes about what you do. That\u2019s all it needs.',
    time: '≈ 45 seconds',
    screen: ScreenKnowledge,
  },
  {
    verb: 'Style',
    title: 'Make it feel like yours.',
    body: 'Pick your colors and decide how much detail it shows. A live preview lets you check before publishing.',
    time: '≈ 20 seconds',
    screen: ScreenTheme,
  },
  {
    verb: 'Install',
    title: 'Install it on your site.',
    body: 'One line, as easy as adding a video. Your agent appears in the corner of your page, ready for visitors.',
    time: '≈ 10 seconds',
    screen: ScreenEmbed,
  },
  {
    verb: 'Done',
    title: 'Visitors get answers on the spot.',
    body: 'Anyone on your page can ask a question and get a clear answer with the source. No waiting, no phone call.',
    time: 'Instant',
    screen: ScreenLive,
  },
  {
    verb: 'Track',
    title: 'Know who\u2019s asking, and from where.',
    body: 'Every conversation is counted — how much your agent is used each day and where your visitors come from. All from your dashboard.',
    time: 'Live',
    screen: ScreenUsage,
  },
]

const stats = [
  {
    num: '70%',
    label: 'of online shoppers leave before finishing their purchase',
    src: 'Baymard Institute',
  },
  {
    num: '44%',
    label: 'of shoppers want their questions answered while they browse',
    src: 'Forrester Research',
  },
  {
    num: '82%',
    label: 'of customers expect an answer the moment they ask',
    src: 'HubSpot Research',
  },
]

onMounted(() => {
  document.title = 'Agent-Plug — Effortless answers for your website visitors'
  const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]')
  if (meta)
    meta.content =
      'Install a friendly agent on your website. Visitors get instant, plain-language answers from your own pages — and stay. Set up in minutes.'
})
</script>

<template>
  <div ref="rootEl" class="lp">
    <a href="#lp-main" class="lp-skip-link">Skip to content</a>

    <!-- ------------------------------------------------------------ nav -->
    <header class="lp-nav">
      <div class="lp-nav-inner">
        <RouterLink to="/" class="lp-brand" aria-label="Agent-Plug home">
          <PlugMark :size="22" :decorative="false" />
          <span>Agent-Plug</span>
        </RouterLink>
        <nav class="lp-nav-links" aria-label="Landing">
          <a class="lp-nav-link" href="#problem">Why</a>
          <a class="lp-nav-link" href="#tour">How it works</a>
          <a class="lp-nav-link" href="#faq">FAQ</a>
        </nav>
        <div class="lp-nav-cta">
          <template v-if="authed">
            <RouterLink class="lp-btn lp-btn-ink lp-btn-sm" to="/dashboard"
              >Open dashboard</RouterLink
            >
          </template>
          <template v-else>
            <RouterLink class="lp-btn lp-btn-ghost lp-btn-sm" to="/login">Log in</RouterLink>
            <RouterLink class="lp-btn lp-btn-ink lp-btn-sm" to="/register">Start free</RouterLink>
          </template>
        </div>
      </div>
    </header>

    <main id="lp-main">
      <!-- ---------------------------------------------------------- hero -->
      <section class="lp-hero" aria-labelledby="lp-hero-title">
        <div class="lp-ambient" aria-hidden="true" />
        <div class="lp-wrap">
          <div class="lp-hero-grid">
            <div class="lp-hero-copy lp-reveal">
              <p class="lp-eyebrow">Effortless answers for your visitors</p>
              <h1 id="lp-hero-title" class="lp-display lp-h1">
                Install a <em class="lp-em">friendly agent</em> on your website.
              </h1>
              <p class="lp-hero-sub">
                It reads your pages once, then answers in plain words — so questions get answered
                on the spot, and visitors stay.
              </p>
              <div class="lp-hero-cta">
                <RouterLink class="lp-btn lp-btn-ink lp-btn-lg" to="/register"
                  >Start free</RouterLink
                >
                <a class="lp-btn lp-btn-ghost lp-btn-lg" href="#tour">See it in action</a>
              </div>
            </div>
            <div class="lp-hero-stage lp-reveal" data-stagger>
              <WidgetMock mode="brief" />
            </div>
          </div>
        </div>
      </section>

      <!-- ------------------------------------------------------ problem -->
      <section id="problem" class="lp-section lp-wrap" aria-labelledby="lp-problem-title">
        <div class="lp-problem-head lp-reveal">
          <h2 id="lp-problem-title" class="lp-display lp-h2">Curious visitors leave too soon.</h2>
          <p class="lp-body">
            People arrive with questions: what do you offer, what does it cost, how does it work? A
            quiet website sends them somewhere else.
          </p>
        </div>

        <div class="lp-stats">
          <div
            v-for="(s, i) in stats"
            :key="s.num"
            class="lp-stat lp-reveal"
            :data-stagger="true"
            :style="{ '--i': i }"
          >
            <div class="lp-stat-num">{{ s.num }}</div>
            <div class="lp-stat-label">{{ s.label }}</div>
            <div class="lp-stat-src lp-mono-meta">{{ s.src }}</div>
          </div>
        </div>
        <p class="lp-stats-note lp-reveal">
          Figures are from public third-party research (Baymard Institute, Forrester Research,
          HubSpot Research), shown for context.
        </p>
      </section>

      <!-- ----------------------------------------------------- solution -->
      <section id="solution" class="lp-section lp-wrap" aria-labelledby="lp-solution-title">
        <div class="lp-solution-grid">
          <div class="lp-reveal">
            <h2 id="lp-solution-title" class="lp-display lp-h2">
              An agent that already knows your business.
            </h2>
            <p class="lp-body">
              Give it your website, your documents, your notes. It reads them once, then answers
              visitors in plain words, pointing to the page it used.
            </p>
          </div>
          <div class="lp-feature-rows lp-reveal" data-stagger>
            <div class="lp-feature-row">
              <div class="lp-feature-title">
                <span class="lp-feature-tick">
                  <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                    <path
                      d="M2.5 7.4 5.4 10.3 11.5 3.8"
                      stroke="currentColor"
                      stroke-width="1.7"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </span>
                Learns from what you have
              </div>
              <p class="lp-feature-desc">
                Your website pages, documents, and notes. Nothing extra to write.
              </p>
            </div>
            <div class="lp-feature-row">
              <div class="lp-feature-title">
                <span class="lp-feature-tick">
                  <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                    <path
                      d="M2.5 7.4 5.4 10.3 11.5 3.8"
                      stroke="currentColor"
                      stroke-width="1.7"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </span>
                Shows where it got the answer
              </div>
              <p class="lp-feature-desc">
                Every answer points to the page it came from, so visitors can check.
              </p>
            </div>
            <div class="lp-feature-row">
              <div class="lp-feature-title">
                <span class="lp-feature-tick">
                  <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                    <path
                      d="M2.5 7.4 5.4 10.3 11.5 3.8"
                      stroke="currentColor"
                      stroke-width="1.7"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </span>
                Quiet in the corner
              </div>
              <p class="lp-feature-desc">
                A small button that opens a chat when visitors need it. No pop-ups, no noise.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- --------------------------------------------------------- tour -->
      <section id="tour" class="lp-tour" aria-labelledby="lp-tour-title">
        <div class="lp-wrap" style="padding-top: 96px; padding-bottom: 0">
          <div class="lp-tour-head">
            <div class="lp-reveal">
              <p class="lp-eyebrow">How it works</p>
              <h2 id="lp-tour-title" class="lp-display lp-h2">Live on your website in minutes.</h2>
              <p class="lp-body lp-tour-summary">
                Six short steps, no manual needed. Here is the whole flow.
              </p>
            </div>
            <div class="lp-tour-meta lp-mono-meta lp-reveal">
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.3" />
                <path
                  d="M8 4.5V8l2.4 1.6"
                  stroke="currentColor"
                  stroke-width="1.3"
                  stroke-linecap="round"
                />
              </svg>
              ≈ 2 min setup · 6 steps
            </div>
          </div>
        </div>

        <div class="lp-wrap">
          <article
            v-for="(step, i) in steps"
            :key="step.verb"
            class="lp-step"
            :style="{ '--i': i }"
          >
            <div class="lp-step-text lp-reveal">
              <p class="lp-step-verb">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path
                    d="M4 2h5v2M9 4l-1.5 6H4.5L3 4"
                    stroke="currentColor"
                    stroke-width="1.3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
                {{ step.verb }}
              </p>
              <h3 class="lp-h3">{{ step.title }}</h3>
              <p class="lp-step-body">{{ step.body }}</p>
              <div class="lp-step-meta lp-mono-meta">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.3" />
                  <path
                    d="M8 4.5V8l2.4 1.6"
                    stroke="currentColor"
                    stroke-width="1.3"
                    stroke-linecap="round"
                  />
                </svg>
                {{ step.time }}
              </div>
            </div>
            <div class="lp-step-screen lp-reveal" data-stagger>
              <component :is="step.screen" />
            </div>
          </article>
        </div>
      </section>

      <!-- ---------------------------------------------------------- faq -->
      <section id="faq" class="lp-section lp-wrap" aria-labelledby="lp-faq-title">
        <div class="lp-faq-wrap">
          <div class="lp-faq-head lp-reveal">
            <h2 id="lp-faq-title" class="lp-display lp-h2">Questions, answered.</h2>
          </div>
          <div class="lp-reveal">
            <LandingFaq />
          </div>
        </div>
      </section>

      <!-- -------------------------------------------------------- cta -->
      <section class="lp-section lp-cta" aria-labelledby="lp-cta-title">
        <div class="lp-ambient" aria-hidden="true" />
        <div class="lp-cta-inner lp-wrap lp-reveal">
          <h2 id="lp-cta-title" class="lp-display lp-h2">{{ SLOGAN }}</h2>
          <p class="lp-cta-sub">
            Create a free account and install your first agent. It takes about two minutes.
          </p>
          <div class="lp-cta-actions">
            <RouterLink class="lp-btn lp-btn-ink lp-btn-lg" to="/register">Start free</RouterLink>
            <RouterLink class="lp-btn lp-btn-ghost lp-btn-lg" to="/login">Log in</RouterLink>
          </div>
          <div class="lp-cta-note">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect
                x="2.5"
                y="7"
                width="11"
                height="6.5"
                rx="1.5"
                stroke="currentColor"
                stroke-width="1.3"
              />
              <path d="M5 7V5.5a3 3 0 0 1 6 0V7" stroke="currentColor" stroke-width="1.3" />
            </svg>
            Free to start · your data stays yours
          </div>
        </div>
      </section>
    </main>

    <!-- ------------------------------------------------------- footer -->
    <footer class="lp-footer">
      <div class="lp-wrap">
        <div class="lp-footer-grid">
          <div>
            <RouterLink to="/" class="lp-brand">
              <PlugMark :size="22" :decorative="false" />
              <span>Agent-Plug</span>
            </RouterLink>
            <p class="lp-footer-tag">{{ SLOGAN }}</p>
          </div>
          <div>
            <p class="lp-footer-col-title">Product</p>
            <ul class="lp-footer-links">
              <li><RouterLink class="lp-footer-link" to="/dashboard">Dashboard</RouterLink></li>
              <li>
                <RouterLink class="lp-footer-link" to="/agents/new">Create an agent</RouterLink>
              </li>
              <li><RouterLink class="lp-footer-link" to="/login">Log in</RouterLink></li>
              <li><RouterLink class="lp-footer-link" to="/register">Register</RouterLink></li>
            </ul>
          </div>
          <div>
            <p class="lp-footer-col-title">For your visitors</p>
            <ul class="lp-footer-links">
              <li><span class="lp-footer-link">Answers from your own pages</span></li>
              <li><span class="lp-footer-link">Every answer shows its source</span></li>
              <li><span class="lp-footer-link">Quiet button, no pop-ups</span></li>
              <li><span class="lp-footer-link">Works on any website</span></li>
            </ul>
          </div>
        </div>
        <div class="lp-footer-bottom">
          <span>© 2025 Agent-Plug</span>
          <span>{{ SLOGAN }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>
