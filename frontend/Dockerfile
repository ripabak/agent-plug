# Agent-Plug frontend — Vue dashboard built with bun, served by `vite preview`
# (the production build of the Vite dev server — same as `bun run preview`).
# No nginx: the dashboard calls the backend directly via VITE_API_BASE (CORS).

FROM node:22-alpine

RUN npm install -g bun

WORKDIR /app

# Install deps first (layer caching).
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

# Base URL of the backend API, baked in at build time.
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

RUN bun run build

EXPOSE 5173

# Serve the production build (dist/) — vite preview, bound to all interfaces.
CMD ["bun", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
