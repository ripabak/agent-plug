import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // Allow access via tunnel / custom domain (e.g. agent-plug.fire.my.id).
  // Vite blocks unknown Host headers by default (DNS-rebinding protection);
  // `true` disables that check for both dev and preview. For a stricter
  // setup, list explicit hosts instead:
  //   allowedHosts: ['agent-plug.fire.my.id']
  server: {
    allowedHosts: true,
  },
  preview: {
    allowedHosts: true,
  },
})
