# LatexLab Phase-1 Integration Runbook

## Scope

This runbook documents phase-1 isolated integration of LatexLab inside VibeLab.

- LatexLab source location: `apps/latexlab/`
- VibeLab routing entry: `/latexlab`
- VibeLab API proxy prefix: `/latexlab-api`
- LatexLab runtime stays independent from VibeLab runtime

## Environment Configuration

### VibeLab `.env`

Set these in the VibeLab root `.env`:

```bash
LATEXLAB_ENABLED=true
LATEXLAB_API_PREFIX=/latexlab-api
LATEXLAB_API_TARGET=http://localhost:8787
LATEXLAB_PROXY_TIMEOUT_MS=30000
LATEXLAB_PORT=8787
LATEXLAB_DATA_DIR=./apps/latexlab/data
LATEXLAB_LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
LATEXLAB_LLM_API_KEY=
LATEXLAB_LLM_MODEL=claude
```

No separate `apps/latexlab/.env` is required. Configure all `LATEXLAB_*` variables in the VibeLab root `.env`.

## Startup Modes

### 1) LatexLab standalone

```bash
npm run latexlab:install
npm run latexlab:dev:backend
npm run latexlab:dev:frontend
```

Expected:
- LatexLab frontend at `http://localhost:5173`
- LatexLab backend at `http://localhost:8787`

### 2) VibeLab + LatexLab integrated (recommended dev workflow)

```bash
npm run latexlab:install
npm run dev
```

Expected:
- VibeLab frontend at `http://localhost:5173`
- VibeLab backend at `http://localhost:3001` (default)
- LatexLab entry available via `http://localhost:5173/latexlab`

### 3) Embedded LaTeX handoff flow (Files -> LatexLab)

1. In VibeLab, open `Files` and click a `.tex` file.
2. Click `Open in LatexLab` in the Files header.
3. VibeLab calls `POST /latexlab-api/projects/open-from-vibelab`.
4. LatexLab creates/reuses a linked project and navigates to:
   - `/latexlab/editor/:projectId?openFile=<relative-tex>&from=vibelab&backTo=<vibelab-path>`
5. LatexLab editor loads directly, without landing page.
6. Use `Back to VibeLab` in LatexLab editor top bar to return.

Linked project behavior:
- Linked project metadata is stored in `apps/latexlab/data/<projectId>/project.json`.
- File reads/writes happen against the original VibeLab workspace path.
- `DELETE /api/projects/:id/permanent` removes only linked metadata, not source workspace files.

## Smoke Test Checklist

### A) VibeLab non-regression

1. Open VibeLab and authenticate as normal.
2. Verify existing tabs/features still work:
   - Chat
   - Files
   - Shell
   - Git
   - ResearchLab
3. Verify existing APIs still respond (example):
   - `GET /health`

### B) LatexLab integrated flow

1. Open `/latexlab` from sidebar shortcut.
2. Verify root route redirects to `/latexlab/projects` (homepage disabled).
3. In VibeLab `Files`, open a `.tex` file and click `Open in LatexLab`.
4. Verify direct navigation to `/latexlab/editor/:projectId` with that file selected.
5. Edit and save file in LatexLab.
6. Return to VibeLab and verify the same source file reflects changes.
7. Verify compile + PDF preview.
8. Verify AI modes are usable (Chat / Agent / Tools) if LLM env is configured.

### C) Disable/rollback safety

1. Set `LATEXLAB_ENABLED=false` in VibeLab `.env`.
2. Restart VibeLab server.
3. Verify VibeLab still starts and works without LatexLab proxy.
4. Optional UI rollback: remove or hide the `/latexlab` sidebar link.

## Troubleshooting

### `/latexlab` returns 503

- Check LatexLab backend service (`LATEXLAB_API_TARGET`).
- Verify VibeLab proxy env values and restart VibeLab.

### LatexLab API calls fail under integrated mode

- Confirm VibeLab env values:
  - `LATEXLAB_API_PREFIX=/latexlab-api`
  - `LATEXLAB_API_TARGET=http://localhost:8787`
- Restart VibeLab and LatexLab backend.

### Port collision during integrated dev

- Use `npm run dev` (VibeLab on 5173, LatexLab backend on 8787).
- If custom ports are needed, adjust `VITE_PORT` and proxy target vars.

## Notes

- Phase-1 is isolation-first; no shared runtime state between VibeLab and LatexLab.
- LatexLab upgrade path is vendor refresh into `apps/latexlab/` with minimal local patching.
