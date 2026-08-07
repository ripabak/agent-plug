/** Shared typing for the widget bridge exposed by backend/app/widget/widget.js.

`widget.js` registers `window.__apwWidgets[agentId]` after it initializes,
with live theme/opts updates (used by the dashboard preview) and a `destroy`
for cleanup. Declared ONCE here so every consumer sees the same type.
*/
import type { ChatTheme } from '@/utils/themes'

export interface WidgetBridge {
  setTheme?: (theme: ChatTheme) => void
  setOpts?: (showThinking: boolean, showTools: boolean) => void
  destroy?: () => void
}

declare global {
  interface Window {
    __apwWidgets?: Record<string, WidgetBridge>
  }
}
