#!/bin/sh
# Claude uygulamasına yüklenecek beceri zip'ini eklentinin kendi dosyalarından üretir.
# Kullanım: sh beceri/olustur.sh [çıktı.zip]
set -e
KOK=$(cd "$(dirname "$0")/.." && pwd)
CIKTI=$(realpath -m "${1:-$KOK/kurgu-yazarligi-atolyesi.zip}")
GECICI=$(mktemp -d)
B="$GECICI/kurgu-yazarligi-atolyesi"
mkdir -p "$B/scripts" "$B/kurallar"
cp "$KOK/beceri/SKILL.md" "$B/"
# Redaktör yönergesi: ajan başlığı (frontmatter) atılır.
awk 'NR==1 && /^---$/ {f=1; next} f && /^---$/ {f=0; next} !f' "$KOK/agents/redaktor.md" > "$B/redaktor.md"
cp "$KOK/scripts/atolye.py" "$B/scripts/"
cp "$KOK/kurallar/tdk.md" "$KOK/kurallar/sik-hatalar.tsv" "$B/kurallar/"
rm -f "$CIKTI"
(cd "$GECICI" && zip -qr "$CIKTI" kurgu-yazarligi-atolyesi)
rm -rf "$GECICI"
echo "$CIKTI"
