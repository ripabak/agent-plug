<script setup lang="ts">
/**
 * LandingView — the public marketing page for Agent-Plug.
 *
 * Narrative (scroll story): problem (visitors leave) → statistics →
 * solution (an agent that knows your site) → a five-screen tour of the real
 * dashboard (create, feed, theme, embed, go live) → FAQ → CTA.
 *
 * Aesthetic: warm monochrome editorial (minimalist-ui protocol). Brand mark:
 * the "plug" (brandkit): chat bubble + socket slots = "plug an agent into
 * your website". All motion is IntersectionObserver-driven; nothing uses a
 * scroll listener; prefers-reduced-motion degrades to static.
 */
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

import '@/assets/landing.css'

import PlugMark from '@/components/landing/PlugMark.vue'
import WidgetMock from '@/components/landing/WidgetMock.vue'
import LandingFaq from '@/components/landing/LandingFaq.vue'
import ScreenCreate from '@/components/landing/steps/ScreenCreate.vue'
import ScreenKnowledge from '@/components/landing/steps/ScreenKnowledge.vue'
import ScreenTheme from '@/components/landing/steps/ScreenTheme.vue'
import ScreenEmbed from '@/components/landing/steps/ScreenEmbed.vue'
import ScreenLive from '@/components/landing/steps/ScreenLive.vue'
import { useReveal } from '@/composables/useReveal'

const auth = useAuthStore()
const authed = computed(() => auth.isAuthenticated)

const rootEl = ref<HTMLElement | null>(null)
useReveal(() => rootEl.value)

const steps = [
  {
    verb: 'Create',
    title: 'Name it, set its tone.',
    body: 'Give the agent a name, a welcome message, and an avatar. This is the first screen of the dashboard.',
    time: '≈ 30 seconds',
    screen: ScreenCreate,
  },
  {
    verb: 'Feed',
    title: 'Teach it your knowledge.',
    body: 'Add URLs, upload a PDF, or paste long text. Each agent keeps its own indexed memory in your database.',
    time: '≈ 45 seconds',
    screen: ScreenKnowledge,
  },
  {
    verb: 'Theme',
    title: 'Make it match your brand.',
    body: 'Pick one of six color presets or set your own colors, and choose whether visitors see the reasoning and tool calls.',
    time: '≈ 20 seconds',
    screen: ScreenTheme,
  },
  {
    verb: 'Embed',
    title: 'Copy one line of HTML.',
    body: 'The snippet is a single script tag. Paste it into your page and the widget appears, bottom right.',
    time: '≈ 10 seconds',
    screen: ScreenEmbed,
  },
  {
    verb: 'Go live',
    title: 'It answers, with sources.',
    body: 'Visitors chat with your knowledge around the clock, and every answer cites where it came from.',
    time: 'Instant',
    screen: ScreenLive,
  },
]

const stats = [
  {
    num: '70%',
    label: 'of checkout carts are abandoned before purchase',
    src: 'Baymard Institute',
  },
  {
    num: '44%',
    label: 'of online shoppers want live answers while they buy',
    src: 'Forrester Research',
  },
  {
    num: '82%',
    label: 'of customers expect an immediate answer when they ask',
    src: 'HubSpot Research',
  },
]

onMounted(() => {
  document.title = 'Agent-Plug - Plug an AI agent into your website'
  const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]')
  if (meta)
    meta.content =
      'Embed a RAG-powered chat agent on any website with one line of HTML. It answers from your own knowledge, with sources.'
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
              <p class="lp-eyebrow">AI chat for any website</p>
              <h1 id="lp-hero-title" class="lp-display lp-h1">
                Plug an <em class="lp-em">AI agent</em> into your website.
              </h1>
              <p class="lp-hero-sub">
                Answer customers instantly from your own knowledge. One line of HTML, no dev team.
              </p>
              <div class="lp-hero-cta">
                <RouterLink class="lp-btn lp-btn-ink lp-btn-lg" to="/register"
                  >Start free</RouterLink
                >
                <a class="lp-btn lp-btn-ghost lp-btn-lg" href="#tour">See how it works</a>
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
          <h2 id="lp-problem-title" class="lp-display lp-h2">
            Visitors ask. Your site goes quiet.
          </h2>
          <p class="lp-body">
            Most websites answer nobody. A question at midnight, a comparison before checkout, a
            policy check in a hurry: the visitor leaves and buys elsewhere.
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
          HubSpot Research). Percentages refer to the cited studies and are shown for context.
        </p>
      </section>

      <!-- ----------------------------------------------------- solution -->
      <section id="solution" class="lp-section lp-wrap" aria-labelledby="lp-solution-title">
        <div class="lp-solution-grid">
          <div class="lp-reveal">
            <h2 id="lp-solution-title" class="lp-display lp-h2">
              An agent that already knows your site.
            </h2>
            <p class="lp-body">
              Agent-Plug reads the pages, PDFs, and notes you give it, then answers in your voice,
              with sources.
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
                Knows your content
              </div>
              <p class="lp-feature-desc">URLs, PDFs, and pasted text, indexed per agent.</p>
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
                Answers with sources
              </div>
              <p class="lp-feature-desc">Every answer links back to the source it came from.</p>
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
                Streams its reasoning
              </div>
              <p class="lp-feature-desc">
                Thinking and tool calls stream in real time; show them or hide them.
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
              <h2 id="lp-tour-title" class="lp-display lp-h2">
                From zero to answering in about two minutes.
              </h2>
              <p class="lp-body lp-tour-summary">
                Five screens, one flow. This is what the dashboard actually looks like.
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
              ≈ 2 min total · 5 screens
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
          <h2 id="lp-cta-title" class="lp-display lp-h2">Paste it. It's live.</h2>
          <p class="lp-cta-sub">Start with a free account and plug in your first agent today.</p>
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
            Free to start · your knowledge stays yours
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
            <p class="lp-footer-tag">One snippet. Any website.</p>
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
            <p class="lp-footer-col-title">Built on</p>
            <ul class="lp-footer-links">
              <li><span class="lp-footer-link">FastAPI + LangChain</span></li>
              <li><span class="lp-footer-link">OpenRouter models</span></li>
              <li><span class="lp-footer-link">PostgreSQL + pgvector</span></li>
              <li><span class="lp-footer-link">Vue 3</span></li>
            </ul>
          </div>
        </div>
        <div class="lp-footer-bottom">
          <span>© 2025 Agent-Plug</span>
          <span>One snippet. Any website.</span>
        </div>
      </div>
    </footer>
  </div>
</template>
