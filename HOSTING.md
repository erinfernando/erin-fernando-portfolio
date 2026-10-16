# erinfernando.com — Hosting & Infrastructure

Last updated: 2026-10-16

## Porkbun Easy PHP Hosting

### SFTP / SSH Access
- **Host:** `sftp.erinfernando.com`
- **Port:** `9022`
- **User:** `erinfernando.com`
- **Auth:** SSH key pair (generate in Porkbun panel first)
- **Web root:** `www/`

### MySQL Database
- **Hostname:** `pixie-db.erinfernando.com`
- **Database name:** `erinfernando_com`
- **User:** `erinfernando_com`
- **Password:** Set by Eris in Porkbun panel (NOT stored here)

### Subdomain-to-Directory Mappings (Easy PHP panel)
These make both `subdomain.erinfernando.com` and `erinfernando.com/path/` work:

| Subdomain | Directory | Notes |
|-----------|-----------|-------|
| `venue` | `/venue` | OK |
| `planner` | `/planner` | NEEDS FIX → `/venue/planner` |
| `rsvp` | `/rsvp` | OK |
| `marketing` | `/marketing` | OK |

### DNS Records Needed
| Type | Host | Value | Status |
|------|------|-------|--------|
| A | `@` | Porkbun Easy PHP IP | Already set |
| A | `hq` | Server IP (Porkbun or future VPS) | NOT YET ADDED |

Old subdomain DNS records for `marketing` and `venue` — check if they exist as separate DNS A/CNAME records (vs just the Easy PHP subdomain mappings above). If they're real DNS records, they can be removed since the Easy PHP mappings handle it.

## Analytics

### Umami (self-hosted)
- **Dashboard:** `https://hq.scriptingwitch.com`
- **erinfernando.com website ID:** `3e0546a0-635e-4789-b7e7-443a71927b4d`
- **wldhorse.com website ID:** `a5788c0a-47cf-4f17-bcd2-febc649218c1` (DO NOT use on erinfernando.com pages)

### Tracking script injection pattern
```html
<script defer src="https://hq.scriptingwitch.com/script.js" data-website-id="3e0546a0-635e-4789-b7e7-443a71927b4d"></script>
<script defer src="https://hq.scriptingwitch.com/recorder.js" data-website-id="3e0546a0-635e-4789-b7e7-443a71927b4d"></script>
```
Injected immediately after `<head>` tag.

### Event tracking
- Download button: `data-umami-event="resume-download"` on the `<a>` tag
- /go/ slugs: No custom events needed — the URL path (`/go/marketing/`, `/go/hipaa/`, etc.) IS the tracking data

## RSVP Backend (PHP)

### Architecture
- **Config:** `rsvp/db-config.php` — loads credentials from a secrets file OUTSIDE www/
- **Secrets file:** `.rsvp-secrets.php` — lives ONE LEVEL ABOVE `www/` so it's not web-accessible
- **Endpoints:** `rsvp-fetch.php` (GET), `rsvp-submit.php` (POST)
- **Rate limiting:** File-based (no DB dependency), stored in a dir outside www/

### Secrets file format (create on server)
```php
<?php
return [
    'host' => 'pixie-db.erinfernando.com',
    'name' => 'erinfernando_com',
    'user' => 'erinfernando_com',
    'pass' => 'DB_PASSWORD_HERE',
];
```

### Config values that need updating for erinfernando.com
| Setting | Current (wldhorse.com) | Needs to be |
|---------|----------------------|-------------|
| `SECRETS_FILE` | `/home/emzmwo4lzlu0/.rsvp-secrets.php` | `/home/erinfernando.com/.rsvp-secrets.php` |
| `RATE_LIMIT_DIR` | `/home/emzmwo4lzlu0/.rsvp-data/` | `/home/erinfernando.com/.rsvp-data/` |
| `RSVP_BASE_URL` | `https://rsvp.wldhorse.com` | `https://erinfernando.com/rsvp` |
| `PLANNER_BASE_URL` | `https://wldhorse.com/planner` | `https://erinfernando.com/venue/planner` |
| `ALLOWED_ORIGINS` | wldhorse.com domains | erinfernando.com domains |

**UNBLOCKED:** Porkbun home directory is `/home/erinfernando.com` (confirmed 2026-10-12).

### Planner → RSVP connection
`venue/planner/wizard.js` line 874:
```js
const RSVP_API_BASE = 'https://rsvp.wldhorse.com';
```
Needs to change to `'https://erinfernando.com/rsvp'` for the demo to talk to the erinfernando.com RSVP backend instead of the live wldhorse.com one.

## Deploy Process

No automated deploy scripts. All uploads are manual via:
1. cPanel File Manager (web UI) — good for small updates
2. SFTP client (FileZilla, WinSCP, etc.) — better for bulk uploads
3. SSH (if enabled) — command-line access

Canonical deploy process doc: `C:\Users\panic\Downloads\AIM-Armory\Processes\production-deployment-process.md`
