# Reusable end-to-end deploy prompt

Paste the block below into a new project's Claude Code session, fill in the
`<...>` placeholders, and it will drive the whole deploy the same way AIRA was
deployed (CloudPanel EC2 host, Docker, host MySQL/Redis reuse, reverse-proxy
sites, GitHub Actions).

Drop the server SSH key into the new project's repo root as `private-key.md`
(the prompt makes the agent gitignore it).

---

```
Deploy this project end-to-end to our shared production server, following our
standard pattern. Work autonomously through all steps, verifying as you go, and
stop to ask me only if a decision is genuinely mine (architecture, destructive
actions, or something that conflicts with what's already on the server).

=== FILL THESE IN ===
- App domain (frontend):     <app.example.rw>
- API domain (backend):      <api-app.example.rw>
- Project type:              <e.g. FastAPI backend + React/Vite SPA + Celery worker>
- Needs a database?          <yes: MySQL / no>
- Needs Redis/queue?         <yes / no>
- Preferred local ports:     <pick 127.0.0.1 ports, e.g. backend 8001, frontend 5174>

=== PORT RULE ===
Before binding any host port, CHECK whether it's already in use
(`sudo ss -tlnp | grep :<port>` or `docker ps`). If it's taken, use the next
free port (+1, then +1 again, etc.) and record the final ports you chose.
Make the CloudPanel reverse-proxy site point at whatever port you actually used.

=== SERVER FACTS (do NOT re-discover destructively) ===
- Host: ubuntu@98.83.16.194 (Ubuntu 24.04, ARM64). SSH key is in the repo root
  as `private-key.md` — it is gitignored; keep it that way.
- Windows OpenSSH rejects the key's default ACL. Before `ssh -i private-key.md`,
  strip the inherited "Authenticated Users"/"Users" entries and grant the owner
  only. Use the PowerShell tool (pipe scripts via stdin to avoid quote mangling;
  PowerShell here-strings add a BOM, so prefer the Bash tool for remote heredocs).
- It's a CloudPanel 6.x box (~1.8 GB RAM) ALSO hosting other projects. Be
  RAM-frugal and never disrupt CloudPanel, its nginx (80/443), MySQL, or Redis.
- REUSE shared infra, don't duplicate it:
    * MySQL: Percona on 127.0.0.1:3306. Get root creds via
      `sudo clpctl db:show:master-credentials`. Create a dedicated db + user with
      `mysql_native_password` (avoid URL-unsafe chars in the password).
    * Redis: system Redis on 127.0.0.1:6379 — pick UNUSED db numbers (check
      `redis-cli info keyspace` first; AIRA already uses 10/11/12).
- Front door = CloudPanel reverse-proxy sites, one per domain:
  `sudo clpctl site:add:reverse-proxy --domainName=<domain> --reverseProxyUrl='http://127.0.0.1:<port>' --siteUser=<user> --siteUserPassword='<pw>'`
  Domains sit behind Cloudflare (TLS at the edge; DNS is already configured).

=== WHAT TO PRODUCE ===
1. A `docker-compose.prod.yml` distinct from any dev compose:
   - Backend/worker on `network_mode: host`, bound to 127.0.0.1:<port>, reusing
     host MySQL (127.0.0.1:3306) and host Redis — NO db/redis containers.
   - Frontend built with ABSOLUTE API URLs (https://<api-domain>/...) and served
     static-only on 127.0.0.1:<port>; don't proxy /api from the frontend container.
   - All ports bind 127.0.0.1 only (and follow the PORT RULE above). Secrets/config
     from `.env.prod` (mode 600, gitignored, lives on the host and survives
     `git reset`). Commit a `.env.prod.example` template. Generate JWT/secret keys
     with `openssl rand`.
2. On the server: install Docker + compose if missing; create the DB/user; clone
   the repo to ~/<project>; write `.env.prod`; bring the stack up; create the two
   CloudPanel reverse-proxy sites.
3. GitHub Actions in `.github/workflows/`:
   - `ci.yml`: run tests + build on push/PR.
   - Path-scoped deploy workflows (one per service) that trigger on push to main,
     SSH in with the `EC2_SSH_KEY` secret (hardcode EC2_HOST/EC2_USER), `git reset
     --hard origin/main`, rebuild ONLY the changed service via the prod compose,
     and health-check the PUBLIC domains.
   - Gitignore `private-key.md`, `.env.prod`, `*.pem`, `*.key`.

=== VERIFY (must all pass before you call it done) ===
- https://<api-domain>/health returns 200 and the API docs load.
- https://<app-domain>/ returns 200 and its JS bundle references the correct
  https://<api-domain> base URL.
- One real DB-backed request works through the public domain (e.g. a login).
- A CORS preflight from the app origin returns the right Access-Control-Allow-Origin.
- Containers use `restart: unless-stopped` and Docker is enabled (survives reboot).

=== TELL ME AT THE END (things you can't do) ===
- The exact local ports you ended up using (in case the PORT RULE bumped them).
- To add the GitHub `EC2_SSH_KEY` secret (paste private-key.md contents) and to
  merge to `main` so auto-deploy tracks the right code.
- Any default seeded credentials I must change.
- Current server RAM/disk headroom and whether a bigger instance is warranted.
```

---

## Notes
- Assumes the **same server and `private-key.md` convention** for every project.
- You still need to do the two things only you can: set the `EC2_SSH_KEY` GitHub
  secret and merge to `main`.
- For very different stacks (pure PHP, Node API, etc.) the compose/workflow parts
  adapt, but the **server pattern** stays the same: reuse host MySQL/Redis, one
  CloudPanel reverse-proxy site per domain, 127.0.0.1-bound ports (with +1 on
  collision).
- Reference implementation: AIRA's `docker-compose.prod.yml`, `.env.prod.example`,
  `police_dashboard/nginx-prod.conf`, and `.github/workflows/`.
