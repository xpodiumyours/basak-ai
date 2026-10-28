#!/usr/bin/env bash
# Oracle Linux 9: existing Vercel web + independent durable worker.
# Run as root after placing the approved environment at /etc/basak/basak.env.
# Does not expose ports or replace the public Vercel deployment.
set -euo pipefail
APP_DIR=/opt/basak
ENV_FILE=/etc/basak/basak.env
[[ $(id -u) == 0 ]] || { echo 'root required' >&2; exit 1; }
source /etc/os-release
[[ $ID == ol && $VERSION_ID == 9* ]] || { echo 'Oracle Linux 9 required' >&2; exit 1; }
[[ -s $ENV_FILE ]] || { echo 'approved environment missing' >&2; exit 1; }
# Small free VMs need headroom before package metadata is loaded.
if [[ ! -e /var/basak-install.swap ]]; then
  fallocate -l 2G /var/basak-install.swap
  chmod 600 /var/basak-install.swap
  mkswap /var/basak-install.swap
fi
swapon --show=NAME --noheadings | grep -qx /var/basak-install.swap || swapon /var/basak-install.swap
grep -q '^/var/basak-install.swap ' /etc/fstab || echo '/var/basak-install.swap none swap sw 0 0' >> /etc/fstab
dnf -y --disablerepo='*' --enablerepo=ol9_baseos_latest --enablerepo=ol9_appstream --setopt=install_weak_deps=False install git python3.12 python3.12-pip
[[ -d $APP_DIR/.git ]] || { echo 'pinned checkout missing' >&2; exit 1; }
id basak >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /sbin/nologin basak
install -d -o basak -g basak -m 700 "$APP_DIR/data"
install -d -o basak -g basak -m 700 "$APP_DIR/data/audit"
chmod 700 /etc/basak
chmod 600 "$ENV_FILE"
python3.12 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --disable-pip-version-check -r "$APP_DIR/requirements.txt"
install -m 644 "$APP_DIR/deploy/oracle/basak.service" /etc/systemd/system/basak.service
install -m 644 "$APP_DIR/deploy/oracle/basak-isci.service" /etc/systemd/system/basak-isci.service
install -d -m 755 /etc/systemd/system/basak-isci.service.d
cat > /etc/systemd/system/basak-isci.service.d/yuva.conf <<EOF
[Service]
ExecStart=
ExecStart=$APP_DIR/.venv/bin/python -m worker.platform --concurrency 1 --poll-seconds 2 --lease-seconds 90
EOF
systemctl daemon-reload
systemctl enable basak.service basak-isci.service
systemctl restart basak.service basak-isci.service
"$APP_DIR/.venv/bin/python" - <<'PY'
import json, time, urllib.request
from dotenv import dotenv_values
token = dotenv_values('/etc/basak/basak.env')['BASAK_WEB_TOKEN']
for attempt in range(3):
    try:
        request = urllib.request.Request('http://127.0.0.1:8000/api/durum', headers={'X-Basak-Token': token})
        with urllib.request.urlopen(request, timeout=90) as response:
            status = json.load(response)
        workers = status.get('platform_isciler') or {}
        if int(workers.get('canli') or 0) >= 1 and status.get('checkpoint_resume') is True:
            print(json.dumps({'platform_isciler': workers, 'checkpoint_resume': True}, ensure_ascii=False))
            break
    except Exception:
        pass
    time.sleep(2)
else:
    raise SystemExit('FAILED: no verified shared-database worker heartbeat')
PY
systemctl is-active basak.service basak-isci.service
echo "revision: $(git -C "$APP_DIR" rev-parse HEAD)"
