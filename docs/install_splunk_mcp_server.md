# Install Splunk MCP Server (Enterprise 10.2.3)

## Verified download (v1.1.3 / build 113)

| Field | Value |
|--------|--------|
| File | `splunk-mcp-server_113.tgz` |
| SHA256 | `1e37205bdd10cf31e25e7d682cd0fa67234ffa65654706963585533d85fa364d` |
| App id | `Splunk_MCP_Server` |
| Version | **1.1.3** |

Verify before install:

```bash
cd ~/Downloads
sha256sum -c <<< '1e37205bdd10cf31e25e7d682cd0fa67234ffa65654706963585533d85fa364d  splunk-mcp-server_113.tgz'
```

Expected: `splunk-mcp-server_113.tgz: OK`

## Install or update from the package

If you already installed from Splunk Web, this **updates** the same app (`-update 1`).

### Recommended: manual install (no Splunk CLI password)

Avoids `Login failed` and bash `!` history issues (`bash: !6138: event not found`).

```bash
export SPLUNK_MCP_PACKAGE="$HOME/Downloads/splunk-mcp-server_113.tgz"
sudo TRUSTOPS_MCP_MANUAL=1 SPLUNK_MCP_PACKAGE="$SPLUNK_MCP_PACKAGE" \
  bash ~/trustops-splunk/scripts/install_splunk_mcp_server.sh
```

### CLI install (optional)

**Passwords containing `!`:** use **single quotes**, not double quotes:

```bash
export SPLUNK_USER='cjalessi'
export SPLUNK_PASSWORD='your!password'   # NOT "..." — double quotes break on !
export SPLUNK_MCP_PACKAGE="$HOME/Downloads/splunk-mcp-server_113.tgz"
bash ~/trustops-splunk/scripts/install_splunk_mcp_server.sh
```

Or read from a file:

```bash
printf '%s' 'your!password' > ~/.splunk_pass && chmod 600 ~/.splunk_pass
export SPLUNK_USER='cjalessi'
export SPLUNK_PASSWORD_FILE=~/.splunk_pass
export SPLUNK_MCP_PACKAGE="$HOME/Downloads/splunk-mcp-server_113.tgz"
bash ~/trustops-splunk/scripts/install_splunk_mcp_server.sh
```

CLI equivalent (non-interactive):

```bash
export SPLUNK_USER="cjalessi"
export SPLUNK_PASSWORD="your-splunk-password"
sudo -u splunk /opt/splunk/bin/splunk install app "$HOME/Downloads/splunk-mcp-server_113.tgz" -update 1 \
  -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
```

### If CLI login still fails

1. Confirm you can sign in at **http://localhost:8000** with the same `SPLUNK_USER` / password.
2. Use **manual install** (extracts the tarball into `etc/apps`):

```bash
export SPLUNK_MCP_PACKAGE="$HOME/Downloads/splunk-mcp-server_113.tgz"
sudo TRUSTOPS_MCP_MANUAL=1 bash ~/trustops-splunk/scripts/install_splunk_mcp_server.sh
```

3. Or skip CLI entirely if **Manage Apps** already shows **Splunk MCP Server** enabled (Splunk Web install is enough for most demos).

## Verify on disk

```bash
ls /opt/splunk/etc/apps/ | grep -i mcp
```

You should see **`Splunk_MCP_Server`**.

In Splunk Web: **Apps → Manage Apps** → **Splunk MCP Server** should be **Enabled**.

## Configure the MCP server

1. Open **Splunk Web** → **Apps** → **Splunk MCP Server**.
2. Complete in-app setup (service account / tokens as prompted).
3. Optional: tune `etc/apps/Splunk_MCP_Server/local/mcp.conf` — see `README/mcp.conf.spec` in the app.
4. Management API endpoint (typical): `https://localhost:8089/services/mcp`

TrustOps does **not** call MCP yet; use this for external agents (Cursor, Claude Desktop, custom FastAPI) once tokens are configured.

## TrustOps integration (later)

Planned path:

- TrustOps backend `AI_PROVIDER=mcp` → MCP client → `run_search` / builtin tools → `InvestigationResponse`
- Keep `ai_agent.py` as fallback for demos

## References

- App README inside package: `Splunk_MCP_Server/README/README_BUILTIN_TOOLS.md`
- Splunkbase: search **Splunk MCP Server**
