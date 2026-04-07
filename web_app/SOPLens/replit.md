# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

## Artifacts

### FIBA AI Frontend (`artifacts/fiba-ai`)
- **Type**: react-vite, served at `/` (previewPath: `/`)
- **Purpose**: Modern dark-themed web app for FIBA AI — an edge-ready, zero-shot action detection and SOP compliance system
- **Backend**: Connects to an external Flask backend at `http://localhost:5000` via Vite dev proxy (`/api → http://localhost:5000`)
- **API calls**: Raw `fetch()` to `/api/...` endpoints (no generated hooks — Flask API is external)
- **Key features**:
  - Action Search mode: video upload + natural language query → SSE progress streaming → rich results (confidence ring, key frames, hand skeletons, trajectories, motion stats, edge profile)
  - SOP Compliance mode: reference video learning + test video validation → step-by-step results with pass/fail
  - Lightbox for full-screen image viewing
  - TypeScript interfaces for all API response types (`src/types/fiba.ts`)
  - Glassmorphism dark theme: purple (#6c5ce7), teal (#00cec9), lavender (#a29bfe), bg #0a0b10

### API Server (`artifacts/api-server`)
- **Type**: Express 5, served at `/api`
- **Purpose**: Internal API server (health check only — not used by FIBA AI frontend)
