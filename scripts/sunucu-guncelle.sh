#!/usr/bin/env bash
# Basak sunucusunu (Oracle) en son main surumune ceker ve servisleri yeniden baslatir.
# Root olarak calistirilir:  bash scripts/sunucu-guncelle.sh
set -euo pipefail

DEPO="${BASAK_DEPO:-/opt/basak}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bu betik root olarak calismali." >&2
    exit 1
fi

cd "$DEPO"

# root kendi deposunda "dubious ownership" hatasi gormesin
git config --global --get-all safe.directory 2>/dev/null | grep -qx "$DEPO" \
    || git config --global --add safe.directory "$DEPO"

echo "== once: $(git log --oneline -1)"
git fetch --prune --quiet
git pull --ff-only
echo "== sonra: $(git log --oneline -1)"

if [ -x .venv/bin/pip ]; then
    .venv/bin/pip install -q -r requirements.txt
else
    echo "UYARI: .venv bulunamadi, pip adimi atlandi." >&2
fi

systemctl restart basak.service basak-isci.service
sleep 3

for servis in basak.service basak-isci.service; do
    printf '%s: %s\n' "$servis" "$(systemctl is-active "$servis")"
done
echo "Bitti. Surum: $(git log --oneline -1)"
