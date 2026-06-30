# Grand Reunion Tour (GRT 2006–2007) — Reunion Web App

A premium-styled reunion hub built with HTML5 / CSS3 / vanilla JS (ES6) on the
frontend and pure-Python (no frameworks) on the backend, per the brief's
technology constraints. Everything lives flat inside this single `reunion`
folder — no subfolders.

## Quick Start

```bash
cd reunion
python3 server.py
```

Then open **http://localhost:8000/index.html**

A SQLite database (`grt_reunion.db`) is created automatically on first run
with demo data, so there is nothing else to install.

### Demo accounts
- Owner: `owner@grt.com` / `GrtOwner@2026`
- Classmate: `ananya.rao@example.com` / `classmate123`

## What's implemented and working right now
- Home dashboard with welcome banner, live countdown, scrolling marquee, announcements, quick actions
- Student directory with live search and city filter chips
- Gallery grid with then/now toggle and a lightbox
- Events timeline with RSVP (going / maybe / can't make it), venue & hotel details
- Message board (post + list, tied to logged-in user)
- Lost & Found (post + list)
- Career opportunities listing
- Secure owner/admin login: PBKDF2-HMAC-SHA256 password hashing, HttpOnly+SameSite session cookies, session expiry, login-attempt logging, rate limiting on login
- Magic invitation system: owner generates a token-based invite link with expiry, viewable history, and a dedicated `invite.html` acceptance flow that lets a classmate set their name/email/optional password plus optional city/profession/school memory right at signup
- "My Profile" page: once joined, a classmate can log in any time and fill in/edit their bio, quote, school memory, phone, city, profession, company, and then/now photo URLs via `/api/profile/update`
- Role-based access (owner / admin / classmate) enforced server-side on every sensitive endpoint
- XSS-safe input sanitization on all user-submitted text, parameterized SQL everywhere (no string-built queries)
- Full luxury glassmorphism design system: animated mesh background, cursor glow, magnetic/ripple buttons, scroll-reveal, skeleton loaders, toasts, modals — responsive from mobile to desktop

## Honest scope note
The original brief asks for a fully enterprise-grade system — QR code invite
generation, email delivery, file-upload photo tagging, password reset emails,
analytics, backups, full audit logging, and a complete production MySQL
deployment. Building all of that to real production quality isn't realistically
deliverable in one pass, so this build prioritizes a genuinely working,
secure, extensible core over a larger pile of stubbed-out features. The
database schema (`schema.sql`) already models every table from the brief
(roles, permissions, invitations, photos, tags, RSVPs, logs, backups, etc.),
so wiring up the remaining endpoints is mostly more of the same pattern
already used in `server.py`.

## Files
- `index.html` — main single-page app shell
- `invite.html` — magic-link invitation acceptance page
- `styles.css` — luxury glassmorphism design system
- `app.js` — SPA routing, API calls, animations, all interactive logic
- `server.py` — Python stdlib backend (http.server), sessions, auth, all APIs
- `schema.sql` — full MySQL production schema (swap in for the SQLite demo DB)
- `grt_reunion.db` — auto-created SQLite database (gitignore in real deployment)

## Moving to real MySQL in production
1. Run `schema.sql` against a MySQL 8+ instance.
2. In `server.py`, replace the `get_db()`/sqlite3 calls with `mysql.connector`
   equivalents — the SQL statements were written to be ANSI-portable to ease
   this swap.
3. Put the server behind HTTPS (e.g. nginx) and move secrets (DB credentials)
   into environment variables instead of hardcoding.
