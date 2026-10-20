# Deploying a stable demo

The local demo works from the repo with `make run` or `python run.py`. For a stable URL
that does not depend on this laptop's tunnel, deploy the Flask app to a small web host.

## Render (recommended)

1. Push this repo to GitHub.
2. Render → **New Web Service** → connect `muen-dev/hackathon-lab`.
3. Runtime: **Python**. Render reads `render.yaml`:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
4. Add environment variables for live sponsors (optional):
   - `NICRRON_API_KEY`, `NICRRON_BASE_URL`, `NICRRON_MODEL`
   - `PRISMTRACE_API_KEY`, `PRISMTRACE_PROJECT_ID`, `PRISMTRACE_ORG_ID`, `PRISMTRACE_HOST`
5. Deploy. Render gives a stable `https://…onrender.com` URL.

## Railway / Docker

The repo includes a `Dockerfile`. Create a Railway project from the GitHub repo;
Railway builds the image and exposes a stable URL. Set the same optional env vars.

## Vercel (current live deployment)

The repo is Vercel-ready:

- `api/index.py` exports the Flask WSGI app.
- `vercel.json` rewrites all paths to the function while preserving the original path.
- `app/services/session_state.py` persists onboarding/application state per browser
  session in Upstash Redis (`KV_REST_API_URL`, `KV_REST_API_TOKEN`), so the flow
  survives Vercel serverless instance switches.
- Generated PDFs are written under `/tmp`; downloads still rebuild from the
  official cached blank PDF.

Deploy:

```bash
vercel link
vercel deploy --prod
```

Project: `hackathon-lab` under Thuy Pham's projects.
Live: https://hackathon-lab.vercel.app

## Caveats

- Demo state is in-process JSON under `data/`; on ephemeral hosts it resets on
  redeploy/restart. That is fine for the synthetic demo.
- Uploads and generated PDFs are synthetic; never add real Gmail credentials or
  taxpayer data to a public deployment.
