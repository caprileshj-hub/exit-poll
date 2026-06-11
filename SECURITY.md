# SECURITY.md — Exit Poll Venezuela

> Security audit trail: documents the 2026-05-01 incident (exposed OpenAI API key),
> the remediation applied, and the accepted risks with their follow-up.

| Parameter | Value |
|-----------|-------|
| Audit date | 2026-05-01 |
| Repository | `caprileshj-hub/exit-poll` |
| Azure App Service | `exit-poll-ve` |
| Azure resource group | `exit-poll-rg` |

---

## What Was Found

- OpenAI notified that an API key from the `estacomp-systems` organization was exposed in the public repository and disabled.
- Git history contained `.env` material that required full history cleanup.
- `.gitignore` did not cover all local secret/config/database patterns requested for this project.
- The `/config` page serialized provider configuration into browser JavaScript, including the `api_key` column if a key was stored in SQLite.
- Azure App Service application settings did not contain `OPENAI_API_KEY` at audit time.
- Azure production SQLite configuration still contained an old OpenAI API key value, causing `/config/test` to prefer the stored value over the environment fallback.
- Azure App Service SCM/Kudu access restrictions allow public access.
- GitHub repository hardening checks showed:
  - Dependabot alerts: disabled.
  - Dependabot security updates: disabled.
  - Secret scanning: disabled at repository level.
  - CodeQL/code scanning: no analysis found.
  - Branch protection for `main`: not enabled.
- Dependency audit of `backend/requirements.txt` found `starlette==0.46.2` affected by:
  - `CVE-2025-54121`, moderate severity, fixed in `starlette==0.47.2`.
  - `CVE-2025-62727`, high severity, fixed in `starlette==0.49.1`.

---

## What Was Fixed

- Rewrote Git history with `git-filter-repo` to remove `.env` and nested `.env` files from all commits.
- Force-pushed sanitized `main` history to GitHub.
- Expired reflogs and ran aggressive garbage collection in both the mirror repository and local working repository.
- Hardened `.gitignore` to include:
  - `.env`
  - `*.db`
  - `*.sqlite`
  - `*.sqlite3`
  - `config.ini`
  - `secrets.yaml`
  - `__pycache__/`
  - `*.pyc`
- Updated `/config` behavior:
  - API keys are removed from the configuration object before rendering the page.
  - Leaving the API key field empty clears the SQLite value and uses the provider environment variable.
- Confirmed backend provider resolution falls back to `OPENAI_API_KEY` when the SQLite API key is empty.
- Enforced Azure HTTPS Only: `httpsOnly=true`.
- Enforced Azure minimum TLS version: `minTlsVersion=1.2`.
- Updated backend dependency pins:
  - `fastapi==0.136.1`
  - `starlette==0.49.1`
- Resolved `CVE-2025-54121` and `CVE-2025-62727` by upgrading `starlette` to `0.49.1`.
- Set `OPENAI_API_KEY` in Azure App Service application settings on 2026-05-01.
- Cleared the stored SQLite API key through `/config/guardar` on 2026-05-01 so the application uses Azure App Settings.
- Updated Azure startup behavior so `requirements.txt` is installed reliably before launching the app.
- Re-ran `pip-audit -r backend/requirements.txt`; result: no known vulnerabilities found.
- Confirmed `/config/test` returned HTTP 200 with `{"ok": true, "provider": "openai"}` after the Azure key migration.

---

## Current Security Posture

- The disabled OpenAI key should be considered permanently compromised and must not be reused.
- No current source/config matches were found for `sk-` in `*.py`, `*.js`, `*.env`, or `*.json`.
- No current `password` matches were found in `*.py` or `*.js`.
- Current `api_key` matches are configuration/schema plumbing only; no literal key values were found.
- Root `requirements.txt` audit result: no known vulnerabilities found.
- Backend `requirements.txt` audit result after remediation: no known vulnerabilities found.
- Azure App Service currently enforces HTTPS and TLS 1.2.
- Azure app settings were listed with secret-like values masked; `OPENAI_API_KEY` is present in Azure App Settings as of 2026-05-01.

---

## Accepted Risk And Follow-Up

- SCM/Kudu public access remains an accepted temporary risk. Restricting it without a deployment allowlist can break the current GitHub Actions deployment path that uses the Azure publish profile. Recommended follow-up: restrict SCM/Kudu to a known administrative IP range or move deployment to an identity-based workflow that supports tighter SCM restrictions.
- GitHub repository security settings require manual enablement in GitHub settings, per audit instruction:
  - Enable Dependabot alerts.
  - Enable Dependabot security updates.
  - Enable secret scanning and push protection.
  - Set up CodeQL/code scanning.
  - Add branch protection for `main` requiring pull request review before merge.
- Existing clones created before the history rewrite may still contain old objects until they are recloned or garbage-collected. Collaborators should reclone from the sanitized repository or run reflog expiration and garbage collection locally.
