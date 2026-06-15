# Deploy TrustOps backend to Railway

Railway can host the **FastAPI backend**. GitHub Pages continues to host the **React UI**.

Railway **cannot** run Splunk for you. The API must reach a Splunk management endpoint (`SPLUNK_HOST` / `SPLUNK_PORT`, usually **8089**) over the network. For a home lab Splunk instance, expose it with a tunnel (ngrok, Cloudflare Tunnel) or use **Splunk Cloud** with a hostname reachable from the public internet.

## Architecture

```
Browser  →  GitHub Pages (React UI)
              ↓  HTTPS
         Railway (FastAPI)
              ↓  Splunk SDK / SAIA REST
         Splunk Enterprise or Splunk Cloud (management API :8089)
```

## 1. Create the Railway service

1. Sign in at [railway.app](https://railway.app).
2. **New Project** → **Deploy from GitHub repo** → select `trustops-splunk`.
3. Railway detects [`railway.toml`](../railway.toml) and builds with the root [`Dockerfile`](../Dockerfile).
4. After deploy, open **Settings → Networking → Generate Domain** (e.g. `https://trustops-api-production.up.railway.app`).

## 2. Set environment variables

In Railway → your service → **Variables**:

| Variable | Required | Example | Notes |
|----------|----------|---------|--------|
| `SPLUNK_USER` | Yes | `cjalessi` | Splunk login |
| `SPLUNK_PASSWORD` | Yes | `***` | Use Railway secrets |
| `SPLUNK_HOST` | Yes | `your-tunnel.ngrok-free.app` | **Not** `localhost` from Railway |
| `SPLUNK_PORT` | Yes | `443` or `8089` | Match your tunnel / Splunk Cloud |
| `SPLUNK_SCHEME` | Yes | `https` | `https` for ngrok / Cloud |
| `SPLUNK_VERIFY_SSL` | | `false` | `true` if using valid public TLS |
| `SPLUNK_AUTH_INDEX` | | `trustops` | |
| `SPLUNK_DECISION_INDEX` | | `trustops_decisions` | |
| `SPLUNK_AGENT_RUN_INDEX` | | `trustops_agent_runs` | |
| `TRUSTOPS_STARTUP_SMOKE_TEST` | | `skip` | Already set in Dockerfile |
| `TRUSTOPS_CORS_ORIGINS` | | `https://midstreamer.github.io` | Default in code; add extras if needed |

Optional: `SPLUNK_MCP_TOKEN`, `SAIA_SOURCE_APP_ID`, `SAIA_USE_MCP=false`.

## 3. Expose local Splunk to Railway (dev / demo)

Example with [ngrok](https://ngrok.com) forwarding Splunk management (HTTPS on 8089):

```bash
ngrok http https://localhost:8089
```

Set on Railway:

- `SPLUNK_HOST` = ngrok hostname (no scheme)
- `SPLUNK_PORT` = `443` (ngrok HTTPS) or the forwarded port ngrok shows
- `SPLUNK_SCHEME` = `https`
- `SPLUNK_VERIFY_SSL` = `false` (ngrok dev certs) or `true` with proper certs

Keep ngrok and Splunk running while demos are active.

## 4. Wire GitHub Pages to Railway

After Railway gives you a public URL (no trailing slash):

1. GitHub repo → **Settings → Secrets and variables → Actions → Variables**
2. Set **`VITE_API_BASE_URL`** = `https://your-service.up.railway.app`
3. Re-run **Deploy GitHub Pages** workflow (or push to `main`)

Users can then open **https://midstreamer.github.io/trustops-splunk/** without the API banner, or use **Connect** once with the Railway URL saved in the browser.

## 5. Verify

```bash
curl -sS https://YOUR-RAILWAY-URL.up.railway.app/health | jq .
curl -sS https://YOUR-RAILWAY-URL.up.railway.app/alerts | jq .
```

Expect `splunk_reachable: true` when Splunk is correctly exposed and credentials are valid.

## Limitations

- **Cost / sleep**: Free Railway tiers may sleep; cold starts add latency for SAIA/agent runs.
- **Splunk dependency**: If Splunk or the tunnel is down, investigation and agent routes return errors; `/health` shows `splunk_reachable: false`.
- **Secrets**: Never commit `SPLUNK_PASSWORD` to git; use Railway variables only.
- **MITRE STIX file**: `data/enterprise-attack.json` is not in git; MITRE agent uses local fallback rules unless you add a build step to download STIX on deploy.

## Local Docker test (optional)

```bash
docker build -t trustops-api .
docker run --rm -p 8001:8001 \
  -e SPLUNK_USER=cjalessi \
  -e SPLUNK_PASSWORD=your-password \
  -e SPLUNK_HOST=host.docker.internal \
  -e SPLUNK_PORT=8089 \
  -e SPLUNK_SCHEME=https \
  -e SPLUNK_VERIFY_SSL=false \
  trustops-api
```

On Linux, replace `host.docker.internal` with your host IP if needed.
