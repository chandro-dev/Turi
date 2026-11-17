#!/usr/bin/env bash
# Despliega Turi en un servidor con Docker por SSH (sin necesitar git en el servidor).
#
#   scripts/deploy-pi.sh chandro@192.168.1.17 '~/contenedores/turi'
#
# Copia el codigo (sin .git, .env ni documentos), reconstruye los contenedores con docker-compose.prod.yml y
# espera a que la API responda. El .env del servidor NO se toca.
set -euo pipefail

TARGET="${1:?uso: deploy-pi.sh usuario@host [ruta-remota]}"
DIR="${2:-~/contenedores/turi}"
cd "$(dirname "$0")/.."

echo ">> Copiando codigo a $TARGET:$DIR"
ssh "$TARGET" "mkdir -p $DIR && cd $DIR && rm -rf turnos-api/app suggestion-service/app web/public"
tar --exclude=.git --exclude='*.docx' --exclude='*.pptx' --exclude=.env --exclude=__pycache__ \
    --exclude=.pytest_cache --exclude=node_modules -czf - . | ssh "$TARGET" "tar -xzf - -C $DIR"

echo ">> Reconstruyendo contenedores"
ssh "$TARGET" "cd $DIR && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans 2>&1 | tail -5"

echo ">> Esperando a la API"
for i in $(seq 1 40); do
  if ssh "$TARGET" "cd $DIR && docker compose exec -T turnos-api python -c \"import urllib.request as u; u.urlopen('http://localhost:8000/api/health', timeout=3)\"" >/dev/null 2>&1; then
    echo ">> Listo"; exit 0
  fi
  sleep 3
done
echo "!! La API no respondio a tiempo. Revisa: docker compose logs turnos-api" >&2
exit 1
