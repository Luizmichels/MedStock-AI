#!/bin/sh
# Backup diário do Postgres de produção (pg_dump compactado), mantendo os
# últimos DIAS_RETENCAO dias. Rode da raiz do repositório ou pelo cron:
#   0 3 * * * /home/ubuntu/MedStock-AI/deploy/backup.sh >> /home/ubuntu/backups/backup.log 2>&1
set -eu

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${DESTINO_BACKUP:-$HOME/backups}"
DIAS_RETENCAO="${DIAS_RETENCAO:-7}"
ARQUIVO="$DESTINO/medstock_$(date +%Y-%m-%d_%H%M).sql.gz"

mkdir -p "$DESTINO"
cd "$RAIZ"
docker compose -f docker-compose.prod.yml exec -T db \
	pg_dump -U postgres --clean --if-exists medstock | gzip > "$ARQUIVO"

# Um dump vazio indica falha; não deixa ele substituir os bons na rotação.
if [ ! -s "$ARQUIVO" ] || [ "$(gzip -cd "$ARQUIVO" | head -c 1 | wc -c)" -eq 0 ]; then
	rm -f "$ARQUIVO"
	echo "$(date '+%F %T') ERRO: backup vazio" >&2
	exit 1
fi

find "$DESTINO" -name 'medstock_*.sql.gz' -mtime +"$DIAS_RETENCAO" -delete
echo "$(date '+%F %T') OK: $ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"
