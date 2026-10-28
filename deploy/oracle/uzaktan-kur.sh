#!/usr/bin/env bash
# Basak — mevcut Oracle sunucusunu uzaktan guncelle/kur.
# Kullanim:
#   bash deploy/oracle/uzaktan-kur.sh opc@SUNUCU_IP [ozel_anahtar]
#   BASAK_SSH_KEY=/yol/anahtar bash deploy/oracle/uzaktan-kur.sh opc@SUNUCU_IP
#
# Sunucuda yaptigi: depoyu main'e getirir, sonra setup.sh'i calistirir.
# setup.sh idempotenttir: web + basak-isci servislerini kurar/gunceller.
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "kullanim: $0 kullanici@sunucu [ozel_anahtar]" >&2
  exit 2
fi
HEDEF="$1"
ANAHTAR="${2:-${BASAK_SSH_KEY:-}}"
REPO="${BASAK_REPO:-https://github.com/xpodiumyours/basak-ai.git}"
DAL="${BASAK_BRANCH:-main}"

SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
if [ -n "$ANAHTAR" ]; then
  SSH+=(-i "$ANAHTAR")
fi

UZAK_KOMUT=$(cat <<EOF
set -euo pipefail
if [ "\$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
if [ ! -d /opt/basak/.git ]; then
  \$SUDO git clone --branch "$DAL" "$REPO" /opt/basak
fi
cd /opt/basak
\$SUDO git fetch origin "$DAL"
\$SUDO git checkout -f "$DAL"
\$SUDO git reset --hard "origin/$DAL"
SETUP=deploy/oracle/setup.sh
. /etc/os-release
if [ "\${ID:-}" = ol ]; then
  SETUP=deploy/oracle/setup-ol9.sh
fi
if [ -n "\$SUDO" ]; then
  \$SUDO env BASAK_BRANCH="$DAL" bash "\$SETUP"
else
  BASAK_BRANCH="$DAL" bash "\$SETUP"
fi
EOF
)

echo "hedef: $HEDEF | dal: $DAL"
"${SSH[@]}" "$HEDEF" "bash -s" <<<"$UZAK_KOMUT"
