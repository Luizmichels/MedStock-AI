#!/bin/bash
# Deploy contínuo do lado do servidor (modelo "pull"): o CD publica as imagens
# no GHCR e este script, agendado no cron, aplica as versões novas. Assim a EC2
# não precisa de nenhuma porta de entrada nem de credencial da AWS no GitHub.
#
# A cada execução:
#   1. atualiza o repositório (compose, Caddyfile, scripts) com a main;
#   2. baixa as imagens latest da API e do frontend;
#   3. se algo mudou: backup do banco, troca dos containers e espera ficarem
#      saudáveis (health check do compose). Além da API e do frontend, confere
#      o proxy (Caddy) e o túnel: um Caddyfile com erro, vindo do repositório,
#      também derruba o site e não pode passar como deploy bem-sucedido;
#   4. se não ficarem: volta às imagens anteriores e marca a nova como
#      rejeitada, para não tentar de novo até sair outra versão.
#
# Cron (a cada 5 minutos):
#   */5 * * * * /bin/bash /home/ubuntu/MedStock-AI/deploy/atualizar.sh >> /home/ubuntu/deploy.log 2>&1
#
# Limites: o rollback volta as imagens, não o banco (as migrações devem ser
# compatíveis com a versão anterior; o backup do passo 3 cobre o pior caso) nem
# os arquivos do repositório.
set -uo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ESTADO="${ESTADO_DEPLOY:-$HOME/.medstock-deploy}"
SERVICOS=(api frontend)            # imagens publicadas pelo CD
MONITORADOS=(api frontend proxy tunnel)  # o que precisa estar de pé após o deploy
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

# Espera os serviços monitorados ficarem de pé; falha se algum não ficar a tempo.
# Quem tem health check no compose (api, frontend, proxy) precisa ficar
# "healthy". O túnel não tem (a imagem do cloudflared não traz shell nem curl
# para rodar um teste), então para ele basta o container estar "running".
aguardar_saude() {
	local limite=$((SECONDS + ESPERA_SAUDE)) s c estado
	for s in "${MONITORADOS[@]}"; do
		while :; do
			c="$(compose ps -q "$s")"
			estado="$( [ -n "$c" ] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$c" 2>/dev/null)"
			[ "$estado" = "healthy" ] || [ "$estado" = "running" ] && break
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
		fi
	fi
	local caddy_mudou=0 recriar_proxy=0
	if [ "$repo_mudou" -eq 1 ] && ! git diff --quiet "$antes" HEAD -- deploy/Caddyfile; then
		caddy_mudou=1
	fi

	# 2. Imagens
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
			# O pull trouxe de novo a imagem rejeitada como :latest. A tag volta
			# para a que está rodando: assim um `compose up` (manual, ou de uma
			# mudança só de configuração no passo 3) não sobe a versão com defeito.
			[ -n "$atual" ] && docker tag "$atual" "$(ref "$s")"
			continue
		fi
		mudaram+=("$s")
	done

	if [ ${#mudaram[@]} -eq 0 ] && [ "$repo_mudou" -eq 0 ]; then
		exit 0
	fi

	# 3. Backup e troca
	log "Atualizando: ${mudaram[*]:-só configuração}"
	if ! sh "$RAIZ/deploy/backup.sh"; then
		log "ERRO: backup falhou; deploy cancelado"
		exit 1
	fi
	# Guarda as imagens em uso para o rollback (tag local, não vai ao GHCR).
	for s in "${mudaram[@]}"; do
		[ -n "${anterior[$s]}" ] && docker tag "${anterior[$s]}" "medstock-ai-$s:anterior"
	done

	# O Caddyfile é montado como arquivo: o container só enxerga a versão nova se
	# for recriado. Antes, valida com o mesmo ambiente do compose; com erro, o
	# proxy segue com a versão que está no ar e o site não cai.
	if [ "$caddy_mudou" -eq 1 ]; then
		if compose run --rm --no-deps -T proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
			recriar_proxy=1
		else
			log "ERRO: o Caddyfile novo é inválido; o proxy segue com a versão anterior (corrija e faça outro deploy)"
		fi
	fi

	compose up -d --remove-orphans
	[ "$recriar_proxy" -eq 1 ] && compose up -d --no-deps --force-recreate proxy

	if aguardar_saude; then
		for s in "${mudaram[@]}"; do rm -f "$ESTADO/rejeitada-$s"; done
		docker image prune -f >/dev/null
		log "OK: deploy concluído (commit $(git rev-parse --short HEAD))"
		exit 0
	fi

	# 4. Rollback
	log "Voltando à versão anterior de: ${mudaram[*]:-nenhuma imagem (só configuração)}"
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
