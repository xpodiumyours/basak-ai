#!/usr/bin/env bash
# Basak — Oracle Always Free kurulum/guncelleme betigi
# Hedef: Ubuntu 24.04 (aarch64), VM.Standard.A1.Flex
# Kullanim:  sudo bash setup.sh
# Idempotent: tekrar calistirmak guvenlidir (kod guncellemesi de boyle yapilir).
#
# Iki servis kurar:
#   basak.service       -> web (uvicorn)
#   basak-isci.service  -> kalici gorev iscisi (worker.platform)
# Isci, web'in istek omrunden bagimsiz calisir; orduyu ayakta tutan parca budur.

set -euo pipefail

APP_DIR=/opt/basak
APP_USER=basak
REPO=https://github.com/xpodiumyours/basak-ai.git
# Dal artik ortamdan degistirilebilir; varsayilan uretim dali.
BRANCH="${BASAK_BRANCH:-main}"
ENV_SRC="$APP_DIR/deploy/oracle/basak.env.ornek"
ENV_DST=/etc/basak/basak.env

if [ "$(id -u)" -ne 0 ]; then
  echo "root olarak calistirin:  sudo bash setup.sh" >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive

# ── 1) Paketler ─────────────────────────────────────────────────────
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git caddy curl \
  ca-certificates unattended-upgrades

# ── 2) Depo (her calistirmada guncel) ───────────────────────────────
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO" "$APP_DIR"
fi
git config --global --add safe.directory "$APP_DIR"
git -C "$APP_DIR" fetch origin "$BRANCH"
git -C "$APP_DIR" checkout -f "$BRANCH"
git -C "$APP_DIR" reset --hard "origin/$BRANCH"

# ── 3) Calisma kullanici + venv + bagimliliklar ─────────────────────
id -u "$APP_USER" >/dev/null 2>&1 || \
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# ── 4) Ortam dosyasi (sirlar burada; varsa DOKUNMA) ─────────────────
mkdir -p /etc/basak
if [ ! -f "$ENV_DST" ]; then
  install -m 600 "$ENV_SRC" "$ENV_DST"
  echo "DIKKAT: $ENV_DST ornekten kopyalandi." >&2
  echo "  Sirlari doldurun, sonra:  systemctl restart basak basak-isci" >&2
fi

# ── 5) Kalici state dizini + yetkiler ───────────────────────────────
mkdir -p "$APP_DIR/data"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 700 /etc/basak

# ── 6) Takas (1 GB RAM'e emniyet payi) ──────────────────────────────
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
  chmod 600 /swapfile
  mkswap -q /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ── 7) Servisler (systemd + Caddy ters vekili) ──────────────────────
install -m 644 "$APP_DIR/deploy/oracle/basak.service" /etc/systemd/system/basak.service
install -m 644 "$APP_DIR/deploy/oracle/basak-isci.service" /etc/systemd/system/basak-isci.service
install -m 644 "$APP_DIR/deploy/oracle/Caddyfile" /etc/caddy/Caddyfile

# Isci yuvasi sunucunun gercek belleğine gore secilir. 1 GB A1'de 1 yuva;
# 2 GB ve uzerinde 2 yuva (her yuva ayri bir gorev calistirir).
MEM_MB=$(awk '/^MemTotal:/{print int($2/1024)}' /proc/meminfo)
GOREV_YUVASI=1
if [ "$MEM_MB" -ge 1800 ]; then GOREV_YUVASI=2; fi
if [ "$MEM_MB" -ge 3600 ]; then GOREV_YUVASI=3; fi
install -d -m 755 /etc/systemd/system/basak-isci.service.d
cat > /etc/systemd/system/basak-isci.service.d/yuva.conf <<EOF
[Service]
ExecStart=
ExecStart=$APP_DIR/.venv/bin/python -m worker.platform --concurrency $GOREV_YUVASI --poll-seconds 2 --lease-seconds 90
EOF
echo "gorev iscisi: ${MEM_MB} MB RAM -> $GOREV_YUVASI eszamanli yuva"

systemctl daemon-reload
systemctl enable --now basak caddy unattended-upgrades basak-isci
systemctl restart basak caddy
systemctl restart basak-isci

# ── 8) Canli dogrulama ──────────────────────────────────────────────
echo "-- bekleniyor (import ~5-15 sn) --"
for _ in $(seq 1 40); do
  curl -fsS -m 2 http://127.0.0.1:8000/api/durum >/dev/null 2>&1 && break
  sleep 1
done
echo "uvicorn :8000/api/durum -> $(curl -fsS -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/durum || echo YOK)"
echo "caddy   :80/            -> $(curl -fsS -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1/ || echo YOK)"

# Isci kalp atisi: veritabanina yazan gercek kanit. Kalp atisi 10 sn'de bir,
# esik 30 sn; bu yuzden en az 12 sn beklenir.
sleep 12
echo "isci servisi            -> $(systemctl is-active basak-isci || true)"
TOKEN=$(sed -n 's/^BASAK_WEB_TOKEN=//p' "$ENV_DST" | tail -1)
if [ -n "$TOKEN" ]; then
  curl -fsS -m 5 -H "X-Basak-Token: $TOKEN" http://127.0.0.1:8000/api/durum \
    | "$APP_DIR/.venv/bin/python" -c \
      'import json,sys; d=json.load(sys.stdin); p=d.get("platform_isciler") or {}; print("platform iscisi canli ->", p.get("canli"), "| checkpoint_resume ->", d.get("checkpoint_resume"))' \
    || echo "isci durumu okunamadi (web kapisi kapali olabilir)"
else
  echo "BASAK_WEB_TOKEN bos: isci durumu API'den okunamaz." >&2
fi

if ! grep -q '^DATABASE_URL=.\+' "$ENV_DST"; then
  echo "UYARI: DATABASE_URL bos. Isci ortak Postgres olmadan BASLAMAZ." >&2
  echo "  Vercel Production ile AYNI DSN yazilmali; yoksa gorevler kuyrukta kalir." >&2
fi

echo "gunluk: journalctl -u basak -f  |  journalctl -u basak-isci -f"
