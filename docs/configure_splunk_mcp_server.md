# Configure Splunk MCP Server (Splunk Web)

For **Splunk Enterprise 10.2.3** with app **Splunk_MCP_Server** v1.1.3 (manual install).

Official references:

- [Configure the Splunk MCP Server](https://help.splunk.com/en/splunk-enterprise/mcp-server-for-splunk-platform/1.1/configure-the-splunk-mcp-server)
- [Connecting to the MCP Server and settings](https://help.splunk.com/en/splunk-enterprise/mcp-server-for-splunk-platform/1.1/connecting-to-the-mcp-server-and-settings)

## Prerequisites

| Item | Your setup |
|------|------------|
| App installed | `Splunk_MCP_Server` under `/opt/splunk/etc/apps/` |
| Splunk Web login | `cjalessi` at http://localhost:8000 |
| REST auth | `bash scripts/verify_splunk_login.sh` returns `[OK]` |

## Step 1 — Enable token authentication

Splunk MCP requires **token authentication** on the instance.

1. Splunk Web → **Settings** → **System** → **Server settings** (or search **Tokens**).
2. Open **Authorization tokens** / **Tokens**.
3. Ensure token authentication is **enabled** for the instance.

If there is no UI toggle, an admin may need `authentication.conf` / `server.conf` per Splunk doc: [Enable token authentication](https://help.splunk.com/en/?resourceId=SplunkCloud_Security_EnableTokenAuth).

Restart only if Splunk prompts you after a change.

## Step 2 — Confirm role capabilities

The MCP app adds:

| Capability | Purpose |
|------------|---------|
| `mcp_tool_execute` | Run MCP tools |
| `mcp_tool_admin` | Manage tools + create MCP tokens |

**`admin`** and **`sc_admin`** already include both (shipped in the app).

For a custom role: **Settings → Roles →** *role* → **Capabilities** → enable **MCP tool execute** and **MCP tool admin**.

Your user **`cjalessi`** should be in **admin** (or a role with those capabilities).

## Step 3 — Open the MCP app in Splunk Web

1. **Apps** → find **Splunk MCP Server**
2. Open the app (home / setup UI)

You should see:

- **MCP server endpoint** URL (copy for clients)
- **Sample MCP client configuration** (JSON)
- **Create encrypted token** (or similar)
- **Tool management** (enable/disable tools)
- **Invalidate keys** (avoid unless you mean to break all tokens)

## Step 4 — Create an encrypted MCP token

In the **Splunk MCP Server** app UI:

1. **Generate** / **Create encrypted token**
2. Set:
   - **User** — usually yourself (`cjalessi`) or a dedicated service user
   - **Expiration** — e.g. 30–90 days for dev
3. **Create** → **copy the token immediately** (shown once)

Required capabilities (from Splunk docs):

| Action | Capabilities |
|--------|----------------|
| Token for yourself | `edit_tokens_own` + `mcp_tool_admin` |
| Token for another user | `edit_tokens_all` + `mcp_tool_admin` |

Admin typically has these. Tokens also appear under **Settings → Tokens**.

**Important:** MCP tokens are **encrypted** and only work for MCP — not as a substitute for normal Splunk REST `-u user:pass` in curl.

## Step 5 — Copy endpoint + configure a client (optional)

From the app UI, copy:

- **MCP endpoint** — typically `https://<host>:8089/services/mcp` (or the URL the app displays)
- **Sample JSON** for Cursor / Claude / `mcp-remote`

Example shape (replace placeholders from the app):

```json
{
  "mcpServers": {
    "splunk-mcp-server": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://localhost:8089/services/mcp",
        "--header",
        "Authorization: Bearer <YOUR_ENCRYPTED_TOKEN>"
      ]
    }
  }
}
```

For **local dev** with self-signed certs, Splunk docs allow `NODE_TLS_REJECT_UNAUTHORIZED=0` in the client env — testing only.

## Step 6 — Tool management (recommended for TrustOps demo)

In the app, review **builtin tools** and enable what you need:

- Core `splunk_*` search tools — on by default
- `saia_*` tools — only if **Splunk AI Assistant** is installed and activated

**Enterprise 10.2.x / CMP note:** MCP `saia_explain_spl` / `saia_generate_spl` and REST `explainspl` / `generatespl` call SAIA **v2** (`saia-api-v2/v2alpha1/spl/*`) and may return **HTTP 400** from the cloud tenant even when Search UI AI works. Search uses the legacy **`/predict`** flow (v1). TrustOps backend calls `/predict` by default (`SAIA_USE_MCP=false`); keep MCP for `splunk_run_query` and other tools.

For TrustOps, useful tools include running searches against `index=trustops` (your auth/decision data).

## Step 7 — Local SSL (Enterprise on localhost)

If MCP clients fail TLS to `https://localhost:8089`, an admin can add (non-production):

`/opt/splunk/etc/apps/Splunk_MCP_Server/local/mcp.conf`:

```ini
[server]
ssl_verify = false
```

Then reload the MCP app (there is no `splunk reload mcp` CLI on Enterprise 10.2):

```bash
set -a
source backend/.env   # SPLUNK_USER + SPLUNK_PASSWORD
set +a
curl -sk -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  -X POST "https://localhost:8089/services/apps/local/Splunk_MCP_Server/_reload"
```

Expect **HTTP 200**. Alternatively: Splunk Web → **Apps** → **Splunk MCP Server** → disable/enable, or `sudo -u splunk /opt/splunk/bin/splunk restart` (heavier).

**Do not use `ssl_verify = false` in production.**

## Step 8 — Verify the app is configured

Splunk Web → **Apps → Manage Apps** → **Splunk MCP Server**:

- **Enabled**
- **Configure** / open app without errors

Optional REST check (session cookie or admin auth — UI is easier):

- Endpoint: `https://localhost:8089/services/mcp`
- Token minting: `https://localhost:8089/services/mcp_token?username=cjalessi&expires_on=+30d` (requires logged-in admin session)

## Your endpoints (from Splunk MCP app)

| URL | Use for |
|-----|---------|
| `https://localhost:8089/services/mcp` | **MCP clients** (`mcp-remote`, Cursor) — preferred |
| `http://localhost:8000/en-US/splunkd/__raw/services/mcp` | Splunk Web–proxied path; same service, use 8089 for external clients |

Store the encrypted token in **`~/.cursor/mcp.json`** (or your client config) — **never** commit it to git. Template: `docs/mcp.client.example.json`.

### Cursor: prefer `url` + `headers` (not `mcp-remote`)

Splunk MCP uses a **static Bearer token**, not OAuth. `mcp-remote` still tries OAuth discovery and often fails with **HTTP 405** on Enterprise 10.2.3 (known issue on app 1.1.3).

Use Cursor’s native remote MCP config:

```json
{
  "mcpServers": {
    "splunk-mcp-server": {
      "url": "https://localhost:8089/services/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_ENCRYPTED_MCP_TOKEN"
      }
    }
  }
}
```

### Token must be the **encrypted MCP token** from the MCP app

| Token type | Looks like | Works for `/services/mcp`? |
|------------|------------|----------------------------|
| **Encrypted MCP token** (from Splunk MCP Server app UI) | Long string, often **two parts separated by `.`** ending in `==` | **Yes** |
| Splunk JWT (`eyJ...`) from generic token UI | Three dot-separated base64 segments | **No** — `Invalid or expired token` |

Always generate/copy the token **inside the Splunk MCP Server app**, not from a generic API token unless the app created it.

**Security:** If the token was pasted in chat or email, regenerate it in the MCP app and invalidate the old one.

## TrustOps integration (later)

TrustOps does **not** call MCP yet. Current flow:

- UI → FastAPI → Splunk (`ai_agent.py`)

Future: backend MCP client using the encrypted token + endpoint from Step 5.

## Troubleshooting

| Issue | What to do |
|-------|------------|
| No **Splunk MCP Server** in Apps | Re-run manual install; restart Splunk |
| Cannot create token | Add `mcp_tool_admin` + `edit_tokens_own` to your role |
| MCP client TLS errors | `ssl_verify = false` in `local/mcp.conf` (dev only) or trust Splunk CA |
| **Invalidate keys** clicked | All MCP tokens stop working — create new tokens |

## Related repo scripts

- `scripts/install_splunk_mcp_server.sh` — install/update app
- `scripts/verify_splunk_login.sh` — test REST login (not MCP token)
