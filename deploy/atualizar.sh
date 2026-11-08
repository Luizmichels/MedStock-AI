#!/bin/bash
# Deploy contínuo do lado do servidor (modelo "pull"): o CD publica as imagens
# no GHCR e este script, agendado no cron, aplica as versões novas. Assim a EC2
# não precisa de nenhuma porta de entrada nem de credencial da AWS no GitHub.
#
# A cada execução:
#   1. atualiza o repositório (compose, Caddyfile, scripts) com a main;
#   2. baixa as imagens latest da API e do frontend;
#   3. se algo mudou: backup do banco, troca dos containers e espera ficarem
#      saudáveis (health check do compose);
#   4. se não ficarem: volta às imagens anteriores e marca a nova como
#      rejeitada, para não tentar de novo até sair outra versão.
#
# Pré-requisito na EC2 (imagens privadas no GHCR):
#   echo "$GHCR_TOKEN" | docker login ghcr.io -u "$USUARIO" --password-stdin
#
# Cron (a cada 5 minutos):
#   */5 * * * * /bin/bash /home/ubuntu/MedStock-AI/deploy/atualizar.sh >> /home/ubuntu/deploy.log 2>&1
#
# Rollback: reverte as imagens, a revisão do banco (alembic downgrade / backup)
# e o commit do repositório caso a nova versão não passe na checagem de saúde.
set -uo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ESTADO="${ESTADO_DEPLOY:-$HOME/.medstock-deploy}"
SERVICOS=(api frontend)
SERVICOS_SAUDE=(api frontend proxy tunnel)
ESPERA_SAUDE=240

compose() { docker compose -f docker-compose.prod.yml "$@"; }
log() { echo "$(date '+%F %T') $*"; }
ref() { echo "$REGISTRO/medstock-ai-$1:$TAG"; }
id_imagem() { docker image inspect -f '{{.Id}}' "$1" 2>/dev/null; }
id_rodando() {
	local c
	c="$(compose ps -q "$1")"
	[ -n "$c" ] && docker inspect -f '{{.Image}}' "$c" 2>/dev/null
}

# Espera todos os serviços monitorados (api, frontend, proxy e tunnel) ficarem
# ativos e saudáveis; falha se algum não ficar a tempo.
aguardar_saude() {
	local limite=$((SECONDS + ESPERA_SAUDE)) s c estado
	for s in "${SERVICOS_SAUDE[@]}"; do
		while :; do
			c="$(compose ps -q "$s")"
			estado="$( [ -n "$c" ] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$c" 2>/dev/null)"
			if [ "$estado" = "healthy" ] || [ "$estado" = "running" ]; then
				break
			fi
			if [ "$SECONDS" -ge "$limite" ]; then
				log "ERRO: $s não ficou saudável (estado: ${estado:-sem container})"
				return 1
			fi
			sleep 5
		done
	done
}

principal() {
	cd "$RAIZ" || exit 1
	mkdir -p "$ESTADO"

	# Mesmas imagens que o compose usa: REGISTRO_IMAGENS e TAG_IMAGEM podem vir
	# do .env (ex.: TAG_IMAGEM=sha-abc1234 para fixar uma versão).
	local REGISTRO_IMAGENS="" TAG_IMAGEM=""
	[ -f .env ] && eval "$(grep -E '^(REGISTRO_IMAGENS|TAG_IMAGEM)=' .env)"
	REGISTRO="${REGISTRO_IMAGENS:-ghcr.io/luizmichels}"
	TAG="${TAG_IMAGEM:-latest}"

	# Uma execução por vez (um deploy pode passar dos 5 minutos do cron).
	exec 9>"$ESTADO/trava"
	flock -n 9 || exit 0

	# 1. Repositório
	local repo_mudou=0 antes
	antes="$(git rev-parse HEAD)"
	if git fetch -q origin main && [ "$antes" != "$(git rev-parse origin/main)" ]; then
		if git merge -q --ff-only origin/main; then
			repo_mudou=1
			log "Repositório: $(git rev-parse --short "$antes") -> $(git rev-parse --short HEAD)"
		else
			log "ERRO: não foi possível atualizar o repositório (alterações locais?)"
			exit 1
		fi
	fi

	# 2. Imagens e verificação de autenticação no GHCR
	if ! docker pull "$REGISTRO/medstock-ai-api:$TAG" >/dev/null 2>&1; then
		log "ERRO: Sem permissão no GHCR. Execute: echo \$GHCR_TOKEN | docker login ghcr.io -u \$USUARIO --password-stdin"
		exit 1
	fi

	if ! compose pull -q "${SERVICOS[@]}"; then
		log "ERRO: falha ao baixar as imagens do GHCR"
		exit 1
	fi

	local s nova atual mudaram=()
	declare -A anterior
	for s in "${SERVICOS[@]}"; do
		nova="$(id_imagem "$(ref "$s")")"
		atual="$(id_rodando "$s")"
		anterior[$s]="$atual"
		[ -z "$nova" ] || [ "$nova" = "$atual" ] && continue
		if [ "$nova" = "$(cat "$ESTADO/rejeitada-$s" 2>/dev/null)" ]; then
			# Restaura a tag local para a imagem em execução, evitando que o pull
			# deixe a imagem rejeitada marcada como :latest.
			[ -n "$atual" ] && docker tag "$atual" "$(ref "$s")"
			continue
		fi
		mudaram+=("$s")
	done

	if [ ${#mudaram[@]} -eq 0 ] && [ "$repo_mudou" -eq 0 ]; then
		exit 0
	fi

	# 3. Backup, registro da migração atual e troca
	log "Atualizando: ${mudaram[*]:-só configuração}"
	if ! sh "$RAIZ/deploy/backup.sh"; then
		log "ERRO: backup falhou; deploy cancelado"
		exit 1
	fi

	local revisao_anterior="" revisao_atual="" ultimo_backup=""
	revisao_anterior="$(compose exec -T api alembic current 2>/dev/null | grep -Eo '^[0-9a-f]+' | head -n 1)"

	# Guarda as imagens em uso para o rollback (tag local, não vai ao GHCR).
	for s in "${mudaram[@]}"; do
		[ -n "${anterior[$s]}" ] && docker tag "${anterior[$s]}" "medstock-ai-$s:anterior"
	done
	# Uma imagem rejeitada que continua sendo a latest não deve subir junto
	# com uma mudança de configuração: fixa a anterior de novo.
	for s in "${SERVICOS[@]}"; do
		nova="$(id_imagem "$(ref "$s")")"
		if [ "$nova" = "$(cat "$ESTADO/rejeitada-$s" 2>/dev/null)" ] && [ -n "${anterior[$s]}" ]; then
			docker tag "${anterior[$s]}" "$(ref "$s")"
		fi
	done

	compose up -d --remove-orphans

	if aguardar_saude; then
		for s in "${mudaram[@]}"; do rm -f "$ESTADO/rejeitada-$s"; done
		docker image prune -f >/dev/null
		log "OK: deploy concluído (commit $(git rev-parse --short HEAD))"
		exit 0
	fi

	# 4. Rollback
	log "Voltando à versão anterior de: ${mudaram[*]:-nenhuma imagem (só configuração)}"

	# Reverte migrações aplicadas pela imagem com falha antes de voltar o container
	if [ -n "$revisao_anterior" ]; then
		revisao_atual="$(compose exec -T api alembic current 2>/dev/null | grep -Eo '^[0-9a-f]+' | head -n 1)"
		if [ -n "$revisao_atual" ] && [ "$revisao_atual" != "$revisao_anterior" ]; then
			log "Revertendo banco de dados da revisão $revisao_atual para $revisao_anterior"
			if ! compose exec -T api alembic downgrade "$revisao_anterior"; then
				log "AVISO: falha no alembic downgrade; restaurando dump do backup.sh"
				ultimo_backup="$(ls -t "${DESTINO_BACKUP:-$HOME/backups}"/medstock_*.sql.gz 2>/dev/null | head -n 1)"
				if [ -n "$ultimo_backup" ]; then
					gzip -cd "$ultimo_backup" | compose exec -T db psql -U postgres -d medstock >/dev/null
				fi
			fi
		fi
	fi

	if [ "$repo_mudou" -eq 1 ]; then
		git reset --hard "$antes"
	fi

	for s in "${mudaram[@]}"; do
		id_imagem "$(ref "$s")" > "$ESTADO/rejeitada-$s"
		docker tag "medstock-ai-$s:anterior" "$(ref "$s")"
	done
	compose up -d
	if aguardar_saude; then
		log "Rollback OK: sistema na versão anterior"
	else
		log "ERRO: rollback também não ficou saudável; verifique manualmente"
	fi
	exit 1
}

# Tudo dentro de uma função: o bash lê o arquivo inteiro antes de executar, então
# o `git merge` do passo 1 pode atualizar este script sem quebrar a execução.
principal "$@"
