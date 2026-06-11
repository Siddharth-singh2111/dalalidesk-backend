# DalaliDesk Backend — Production Deploy Guide

Deploy the backend on a fresh Ubuntu 22.04/24.04 VPS, fronted by nginx with a free Let's Encrypt TLS cert. Frontend lives on Vercel (separate). Total time: ~45 min the first time.

**Assumptions:**
- You have root/sudo SSH access to the VPS.
- The VPS is reachable on a public IP.
- Postgres is already installed natively on the server (per your earlier setup).
- You don't have a domain — we'll use a free DuckDNS subdomain.

---

## 1. Get a hostname (DuckDNS)

Vercel serves HTTPS only. Browsers block HTTP API calls from HTTPS pages (mixed content). We need an HTTPS endpoint, which needs a domain. DuckDNS gives a free subdomain in 2 minutes.

1. Go to <https://www.duckdns.org> → log in with GitHub/Google.
2. Pick a subdomain, e.g. `dalalidesk` → it becomes `dalalidesk.duckdns.org`.
3. In the "current ip" field, paste your VPS public IP. Click **update ip**.
4. Verify: `ping dalalidesk.duckdns.org` from your laptop should resolve to your VPS IP.

(Optional but recommended: install the DuckDNS auto-update cron on the VPS so the record refreshes if the IP changes. Skip if your VPS IP is static.)

---

## 2. Server prep (one-time)

SSH in as root or a sudoer. From here, replace `dalalidesk.duckdns.org` with your actual subdomain.

```bash
sudo apt update && sudo apt -y upgrade
sudo apt install -y git python3.9 python3.9-venv python3-pip \
                    nginx certbot python3-certbot-nginx \
                    libpq-dev build-essential ufw
```

If `python3.9` isn't available on your distro's apt repo (Ubuntu 24.04 default is 3.12), add the deadsnakes PPA:
```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt update
sudo apt install -y python3.9 python3.9-venv
```

### Create an unprivileged user for the service

```bash
sudo useradd -r -m -d /opt/dalalidesk -s /usr/sbin/nologin dalalidesk
```

### Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status
```

---

## 3. Postgres — schema and user

(You said Postgres is already installed. Replace `<DB_PASSWORD>` with a strong password you generate; do NOT reuse anything.)

```bash
sudo -u postgres psql <<EOF
CREATE USER dalalidesk WITH PASSWORD '<DB_PASSWORD>';
CREATE DATABASE dalalidesk OWNER dalalidesk;
GRANT ALL PRIVILEGES ON DATABASE dalalidesk TO dalalidesk;
EOF
```

Apply the schema. We'll load it as the postgres superuser to handle the sequence/extension privileges cleanly, then ownership stays with the dalalidesk user via the GRANT above.

```bash
# Clone the repo first (next step) — then come back and run:
sudo -u postgres psql -d dalalidesk -f /opt/dalalidesk/hca_backend/API_Database/holani_cloth_agency.sql
```

If you want the v2 dalali_entry / firm tables ready from day one (recommended), the SQLAlchemy `db.create_all()` in `app.py` will create them on first backend boot — no manual SQL needed.

---

## 4. Clone the backend and set up the venv

```bash
sudo mkdir -p /opt/dalalidesk
sudo chown dalalidesk:dalalidesk /opt/dalalidesk
sudo -u dalalidesk bash <<'EOF'
cd /opt/dalalidesk
git clone https://github.com/Siddharth-singh2111/dalalidesk-backend.git hca_backend
python3.9 -m venv hca_venv
source hca_venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r hca_backend/requirements.txt
EOF
```

---

## 5. Backend `.env`

Generate secrets and write the `.env`:

```bash
sudo -u dalalidesk bash <<'EOF'
cd /opt/dalalidesk/hca_backend
cp .env.example .env
EOF

# Generate a JWT secret and a DB password placeholder. Edit .env with these.
sudo -u dalalidesk python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
```

Edit `/opt/dalalidesk/hca_backend/.env` (`sudo -u dalalidesk nano /opt/dalalidesk/hca_backend/.env`) — set:

```
DB_NAME=dalalidesk
DB_USER=dalalidesk
DB_PASSWORD=<the password from step 3>
DB_PORT=5432
DB_HOST=127.0.0.1

QUERY_REMOTE=false

JWT_SECRET_KEY=<the value you just generated>

# Replace with your actual Vercel frontend URL once you deploy it.
# Add the production URL and any preview URLs you'd like to allow.
CORS_ALLOWED_ORIGINS=https://dalalidesk.vercel.app
```

Permissions: the `.env` contains secrets — restrict it.
```bash
sudo chmod 600 /opt/dalalidesk/hca_backend/.env
sudo chown dalalidesk:dalalidesk /opt/dalalidesk/hca_backend/.env
```

---

## 6. Install the systemd service

The repo ships a template at `deploy/dalalidesk-backend.service`. Copy and enable:

```bash
sudo cp /opt/dalalidesk/hca_backend/deploy/dalalidesk-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dalalidesk-backend
sudo systemctl status dalalidesk-backend --no-pager
```

You should see `active (running)`. The service exposes the backend on `127.0.0.1:5050` only — nginx will proxy it.

If startup fails, tail logs:
```bash
journalctl -u dalalidesk-backend -e
```

---

## 7. nginx reverse proxy

```bash
sudo cp /opt/dalalidesk/hca_backend/deploy/nginx-site.conf.example /etc/nginx/sites-available/dalalidesk
sudo sed -i 's/DOMAIN/dalalidesk.duckdns.org/g' /etc/nginx/sites-available/dalalidesk
sudo ln -s /etc/nginx/sites-available/dalalidesk /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Verify HTTP works (you should get a redirect):
```bash
curl -I http://dalalidesk.duckdns.org/api/login
```

---

## 8. TLS via Let's Encrypt

```bash
sudo certbot --nginx -d dalalidesk.duckdns.org \
  --non-interactive --agree-tos -m your-email@example.com --redirect
```

Certbot edits the nginx config to add the cert paths and reloads nginx. Verify:
```bash
curl -I https://dalalidesk.duckdns.org/api/login   # expect 401 (unauthorized — that's fine, just means it reached the API)
```

Cert auto-renewal is set up via `certbot.timer`. Confirm:
```bash
sudo systemctl list-timers | grep certbot
```

---

## 9. Frontend (Vercel) configuration

In the Vercel dashboard for the frontend project:

1. **Settings → Environment Variables** → add:
   - `VITE_API_URL` = `https://dalalidesk.duckdns.org/api` — applies to *Production* (and *Preview* if you want)
2. Trigger a redeploy (Deployments → ⋯ → Redeploy → tick "use existing build cache: no").
3. After deploy, note the Vercel URL (e.g. `https://dalalidesk.vercel.app`) and **come back to step 5** to add it to `CORS_ALLOWED_ORIGINS`. Restart the backend:
   ```bash
   sudo systemctl restart dalalidesk-backend
   ```

---

## 10. End-to-end smoke test

From the Vercel URL, open the login page. You should see the DalaliDesk wordmark, log in with `admin` / `admin5555`, and land on the dashboard.

If you hit "Failed to fetch":

| What you see | What to check |
|---|---|
| Browser DevTools shows CORS error | `CORS_ALLOWED_ORIGINS` doesn't include the exact Vercel origin — fix .env, `systemctl restart dalalidesk-backend`. |
| Network tab shows the request hit `vercel.app/api/...` not `dalalidesk.duckdns.org/api/...` | `VITE_API_URL` wasn't applied. Redeploy on Vercel **with cache disabled**. |
| `502 Bad Gateway` from nginx | Backend isn't running — `journalctl -u dalalidesk-backend -e`. |
| `401` on login | Wrong creds. Reset: `sudo -u postgres psql -d dalalidesk -c "UPDATE users SET password_hash = '\$2b\$12\$exsUIERNQnlTDLqhYqAS3uRFCYu6H9C1ru4OvdIUrH0QLrSfjHu9G' WHERE username='admin';"` — that resets to `admin5555`. |

---

## 11. Day-2 operations

**Backups (do this!)**
```bash
sudo -u postgres pg_dump dalalidesk > /opt/dalalidesk/backups/dalalidesk-$(date +%F).sql
```
Wire it as a daily cron:
```bash
sudo crontab -e
# add: 0 2 * * * sudo -u postgres pg_dump dalalidesk > /opt/dalalidesk/backups/dalalidesk-$(date +\%F).sql && find /opt/dalalidesk/backups -name '*.sql' -mtime +14 -delete
```

**Deploying a new backend version**
```bash
sudo -u dalalidesk bash <<'EOF'
cd /opt/dalalidesk/hca_backend
git pull
source /opt/dalalidesk/hca_venv/bin/activate
pip install -r requirements.txt
EOF
sudo systemctl restart dalalidesk-backend
```

**Deploying a new frontend version** — happens automatically when you push to GitHub if you connected Vercel to the repo. If not, run `npx vercel --prod` from your laptop.

**Logs**
- Backend: `journalctl -u dalalidesk-backend -f`
- nginx access: `sudo tail -f /var/log/nginx/access.log`
- nginx errors: `sudo tail -f /var/log/nginx/error.log`

**Changing the admin password**
- Through the app (Profile → set new password). Do this the moment the client is set up.

---

## Security checklist before going live

- [ ] Default `admin` password changed via the app.
- [ ] `JWT_SECRET_KEY` set in `.env` (not the dev fallback).
- [ ] `CORS_ALLOWED_ORIGINS` set to ONLY the Vercel domain.
- [ ] `.env` is `chmod 600` and owned by `dalalidesk`.
- [ ] TLS cert active (`https://...` works, `http://` redirects).
- [ ] `ufw status` shows only OpenSSH and Nginx Full open.
- [ ] Postgres `pg_hba.conf` doesn't expose port 5432 to the world (default Ubuntu install is `local`/`127.0.0.1` only — verify with `sudo ss -tlnp | grep 5432`).
- [ ] Daily backups configured.
