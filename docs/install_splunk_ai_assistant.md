# Install Splunk AI Assistant (Enterprise 10.2.3)

TrustOps runs on **Splunk Enterprise 10.2.3**. Splunk AI Assistant is a **separate app** (Splunkbase app **7245**) that uses **Cloud Connected** for on-prem — it is not installed by default.

## What is already on your instance

- `enable_search_ai_assistant = true` in `/opt/splunk/etc/system/default/web-features.conf`
- Search UI assets under `/opt/splunk/share/splunk/search_mrsparkle/exposed/build/pages/ai-assistant/`
- **No** `splunk_ai_assistant` (or similar) app under `/opt/splunk/etc/apps/`

You still need the **Splunkbase app** plus **EULA + cloud activation** before the assistant works end-to-end.

## Prerequisites

1. **Splunk.com account** (same org as your license).
2. **EULA** — [Splunk AI Assistant registration](https://www.splunk.com/en_us/download/ai-assistant.html). Splunk reviews approval (up to ~72 hours); you get email when download is unlocked.
3. **Outbound HTTPS** from the search head to `*.scs.splunk.com` on port **443** (firewall/proxy).
4. **Admin** on Splunk Web (`cjalessi` or equivalent).

## Option A — Install from Splunk Web (recommended)

1. Open **http://localhost:8000** and sign in.
2. **Apps** → **Browse more apps** (or **Find more apps**).
3. Search **“AI Assistant”** → **Splunk AI Assistant** (Splunkbase **7245**, v2.x for 10.2).
4. **Install** (requires Splunk.com login; download is tied to the EULA-approved account).
5. Open the app and complete **Cloud Connected** setup:
   - **Begin setup** → company, region, email → **tenant code**
   - Submit tenant code: [tenant code form](https://www.splunk.com/en_us/form/tenantcodesubmit.html)
   - Wait for **activation token** email (~2 business days; contact `splunkai@cisco.com` if delayed)
   - **Connect to cloud** with the token
6. In **Search**, open the assistant panel (sparkle / AI control near the search bar).

## Option B — Install from downloaded package (CLI)

After EULA approval, download the `.spl` / `.tgz` from [Splunkbase app 7245](https://splunkbase.splunk.com/app/7245/) (must be logged in).

```bash
# List what you actually downloaded (do not copy angle-bracket placeholders)
ls ~/Downloads/*.spl

export SPLUNK_AI_PACKAGE="$HOME/Downloads/splunk-ai-assistant_200.spl"   # real filename from ls
bash scripts/install_splunk_ai_assistant.sh
```

Then complete **Cloud Connected** activation in Splunk Web (same as Option A, step 5).

## Verify installation

```bash
ls /opt/splunk/etc/apps/ | grep -i ai
```

Or in Splunk Web: **Apps** → **Manage Apps** → search **AI**.

Authenticated REST (optional):

```bash
export SPLUNK_USER="your-user"
export SPLUNK_PASSWORD="your-password"
curl -sk -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  "https://localhost:8089/services/apps/local?output_mode=json&count=0" \
  | python3 -c "import sys,json; print([e['name'] for e in json.load(sys.stdin)['entry'] if 'ai' in e['name'].lower()])"
```

## TrustOps integration (after Assistant works)

- Use Assistant in Splunk for SPL help on `index=trustops` queries.
- Keep TrustOps `ai_agent.py` as the demo default until you wire `AI_PROVIDER=splunk_ai` in the backend.

## References

- [Install Splunk AI Assistant](https://docs.splunk.com/Documentation/AIAssistant/latest/User/InstallAIAssistant)
- [Activate through cloud connected](https://docs.splunk.com/Documentation/AIAssistant/latest/User/CloudConnected)
- [Splunkbase app 7245](https://splunkbase.splunk.com/app/7245/)
