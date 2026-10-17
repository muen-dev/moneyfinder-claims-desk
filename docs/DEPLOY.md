# Deploying a stable demo

The local demo works from the repo with `make run` or `python run.py`. For a stable URL
that does not depend on this laptop's tunnel, deploy the Flask app to a small web host.

## Render (recommended)

1. Push this repo to GitHub.
2. Render → **New Web Service** → connect `muen-dev/moneyfinder-claims-desk`.
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

## Vercel

Vercel is great for the static marketing page but this demo is a stateful Flask app
(onboarding state, generated PDFs, fixture edits). Serverless filesystem state is
ephemeral, so use Render/Railway for the full demo. If you only need a stable
redirect or the landing page, a Vercel static project is fine.

## Caveats

- Demo state is in-process JSON under `data/`; on ephemeral hosts it resets on
  redeploy/restart. That is fine for the synthetic demo.
- Uploads and generated PDFs are synthetic; never add real Gmail credentials or
  taxpayer data to a public deployment.
