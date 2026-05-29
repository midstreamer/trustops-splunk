# Troubleshoot Splunk Web login failed

## Use the correct URL

| Wrong | Correct |
|-------|---------|
| `http://localhost:80000` | **`http://localhost:8000`** |

Splunk Web listens on port **8000** (not 80000).

## Use the correct username

| Wrong | Correct |
|-------|---------|
| `chadalessi@yahoo.com` | **`cjalessi`** (local Splunk account) |

Your instance has a Splunk user folder: `/opt/splunk/etc/users/cjalessi/`

Splunk Web does **not** use your email as the login name unless you explicitly created a user with that name.

## Password tips

- Type the password **manually** in the browser (avoid autofill from a different site).
- If the password contains `!`, `#`, or `$`, make sure Caps Lock is off.
- The same password must work for REST if you test:

```bash
set +H
export SPLUNK_USER='cjalessi'
export SPLUNK_PASSWORD='your-password'
bash scripts/verify_splunk_login.sh
```

- **`[OK]`** → password is correct; clear browser cache/cookies for localhost:8000 or try a private window.
- **`[ERROR] HTTP 401`** → password does not match what Splunk has stored.

## Reset password (you know the current password)

```bash
set +H
export SPLUNK_USER='cjalessi'
export SPLUNK_NEW_PASSWORD='NewPassword123!'
export SPLUNK_ADMIN_USER='cjalessi'
export SPLUNK_ADMIN_PASSWORD='current-password-that-works-for-CLI'
sudo bash scripts/reset_splunk_user_password.sh
```

Then sign in at http://localhost:8000 with `cjalessi` and `SPLUNK_NEW_PASSWORD`.

## Reset password (nothing works — bootstrap)

Your `verify_splunk_login.sh` returned **HTTP 401** — Splunk does not have the password you exported. Use bootstrap:

```bash
set +H
export SPLUNK_BOOTSTRAP_USER='cjalessi'
export SPLUNK_BOOTSTRAP_PASSWORD='TempPass123!'   # pick a NEW temporary password
sudo bash ~/trustops-splunk/scripts/bootstrap_splunk_admin.sh
```

Then:

1. Log in at **http://localhost:8000** with `cjalessi` and `SPLUNK_BOOTSTRAP_PASSWORD`
2. **Settings → Users** → set a permanent password
3. **Delete user-seed** (required):

```bash
sudo rm /opt/splunk/etc/system/local/user-seed.conf
sudo -u splunk /opt/splunk/bin/splunk restart
```

4. Verify the **new** password:

```bash
set +H
export SPLUNK_USER='cjalessi'
export SPLUNK_PASSWORD='your-new-permanent-password'
bash ~/trustops-splunk/scripts/verify_splunk_login.sh
```

Manual steps (same process) are documented below if you prefer not to use the script.

## Account lockout

After many failed attempts, wait a few minutes or restart Splunk:

```bash
sudo -u splunk /opt/splunk/bin/splunk restart
```

## TrustOps after fixing login

Update exports everywhere you use Splunk:

```bash
export SPLUNK_USER='cjalessi'
export SPLUNK_PASSWORD='your-working-password'
```

Restart the backend so `/health` shows `splunk_reachable: true`.
