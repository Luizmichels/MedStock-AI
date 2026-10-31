# MedStock AI — Backend

API de análise preditiva de consumo de insumos hospitalares, construída com **FastAPI + SQLAlchemy + PostgreSQL**. O sistema importa o histórico de consumo, classifica os itens (ABC/XYZ), treina modelos de séries temporais e gera previsões de demanda por item, além de dashboard e exportação de relatórios.

## Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** (ORM) + **PostgreSQL**, com **Alembic** para migrações
- **JWT** (`python-jose`) para autenticação e **bcrypt** para hash de senha
- **Pandas / NumPy** — pipeline de dados
- **LightGBM / statsmodels / skforecast** — modelos de previsão
- **reportlab / openpyxl** — exportação em PDF e Excel
- **pytest / pytest-cov / respx** — testes e cobertura

## Funcionalidades

| Área | Rotas principais |
|---|---|
| **Autenticação** | `POST /auth/login`, `/auth/definir-senha`, `/auth/esqueci-senha`, `/auth/redefinir-senha`, `/auth/reenviar-ativacao` |
| **Empresas / acesso** | solicitação pública de acesso (com rate limit), aprovação e gestão pelo super admin |
| **Usuários** | gestão de usuários por empresa (isolamento de dados entre empresas) |
| **Importação** | `POST /importacoes/upload` (CSV/Excel, processado em segundo plano), `GET /importacoes/` e `GET /importacoes/{id}` para acompanhar o status |
| **Consulta** | `GET /itens/`, `GET /itens/{id}`, `GET /consumos/`, `GET /consumos/serie/{item_id}` (paginados) |
| **Previsões (ML)** | `POST /previsoes/treinar`, `GET /previsoes/modelos`, `POST /previsoes/modelos/{id}/ativar`, `GET /previsoes/`, `GET /previsoes/itens-omitidos`, `GET /previsoes/status-treino` |
| **Dashboard** | `GET /dashboard/resumo`, `/consumo-mensal`, `/consumo-por-local`, `/classificacao-abc`, `/abc-xyz`, `/top-itens` |
| **Exportação** | `GET /exportacoes/previsoes\|consumo\|metricas?formato=pdf\|xlsx` |
| **Sistema** | `GET /health` |

Documentação interativa (Swagger) em `http://localhost:8000/docs`.

### Módulo de Machine Learning

O pipeline de previsão vive em `app/services/ml/` e é o núcleo do trabalho:

- **Séries mensais por item**, com meses sem consumo preenchidos com zero (demanda intermitente é sinal, não dado faltante).
- **Elegibilidade (RN06):** itens com menos de 3 meses de histórico ficam de fora do treino e são reportados em `/previsoes/itens-omitidos`.
- **5 algoritmos:** SMA, SARIMA, Holt-Winters, Random Forest e Gradient Boosting.
- **Validação walk-forward** (treino expansivo, sem vazamento temporal), comparando os algoritmos por MAPE, MAE e RMSE.
- **Seleção por item:** cada item elegível é previsto pelo algoritmo de menor MAPE *para aquele item*; a escolha fica registrada no modelo ativo.
- O treino roda em segundo plano (`BackgroundTasks`) e nunca dentro do request.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (forma recomendada de rodar o projeto)
- Python 3.12 ou superior (só necessário se for rodar/testar sem Docker)

## Configuração (`.env`)

Crie um arquivo `.env` dentro de `Backend/` com as seguintes variáveis:

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | String de conexão do PostgreSQL (ex: `postgresql+psycopg://postgres:SENHA@localhost:5432/medstock`) |
| `TEST_DATABASE_URL` | *(opcional)* Banco usado pelos testes. Se ausente, a suíte usa SQLite em memória |
| `SECRET_KEY` | Chave usada para assinar os tokens JWT |
| `ALGORITHM` | Algoritmo do JWT (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de login, em minutos (default `60`) |
| `DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES` | Validade dos links de definição/redefinição de senha, em minutos (default `2880` = 48h) |
| `FRONTEND_URL` | URL base do frontend, usada nos links de e-mail e no CORS (default `http://localhost:3000`) |
| `SUPER_ADMIN_EMAIL` | E-mail do super admin criado automaticamente no primeiro start |
| `SUPER_ADMIN_SENHA` | Senha do super admin criado automaticamente no primeiro start |
| `EMAIL_REMETENTE` | E-mail usado para enviar as notificações (ex: Gmail) |
| `SENHA_EMAIL` | Senha de app do e-mail remetente (no Gmail, precisa ser uma [senha de app](https://myaccount.google.com/apppasswords), não a senha normal da conta) |
| `SMTP_HOST` / `SMTP_PORT` | Servidor SMTP (default `smtp.gmail.com:587`) |
| `POSTGRES_PASSWORD` | Senha do usuário `postgres` — usada pelo `docker-compose.yml` para subir o banco (deve ser a mesma de `DATABASE_URL`) |
| `DOMINIO` | *(produção)* Domínio usado pelo proxy Caddy para emitir o certificado HTTPS (default `localhost`) |

O `.env` nunca deve ser commitado (já está no `.gitignore`).

## Rodando com Docker (recomendado)

Com o Docker Desktop aberto e o `.env` configurado:

```bash
docker compose up --build -d
```

Sobe três serviços:
- **`db`**: PostgreSQL 16, com os dados persistidos em um volume nomeado (`postgres_data`).
- **`api`**: aplicação FastAPI na porta `8000`. No start, o container roda `alembic upgrade head` (aplica as migrações) e sobe o Uvicorn.
- **`proxy`**: Caddy como proxy reverso, com HTTPS automático (portas 80/443).

No primeiro start, o schema é criado pelas migrações e o usuário super admin é gerado a partir de `SUPER_ADMIN_EMAIL`/`SUPER_ADMIN_SENHA`.

Verifique se subiu corretamente:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Comandos úteis

| Comando | Efeito |
|---|---|
| `docker compose up -d` | Sobe os serviços (sem rebuildar a imagem) |
| `docker compose up --build -d` | Rebuilda a imagem da API e sobe os serviços — use depois de mudar `requirements.txt` ou o `Dockerfile` |
| `docker compose logs -f api` | Acompanha os logs da API em tempo real |
| `docker compose down` | Para os containers (mantém os dados do banco) |
| `docker compose down -v` | Para os containers **e apaga os dados do banco** (reset completo) |

## Migrações (Alembic)

O schema é versionado com Alembic (pasta `alembic/`). Em Docker, as migrações são aplicadas automaticamente no start da API; localmente:

```bash
alembic upgrade head                               # aplica todas as migrações
alembic revision --autogenerate -m "descricao"     # gera uma nova migração a partir dos modelos
```

Por padrão o Alembic usa a `DATABASE_URL` do `.env`. É possível apontar para outro banco com a variável `ALEMBIC_DATABASE_URL`.

## Rodando sem Docker

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Nesse caso, `DATABASE_URL` no `.env` deve apontar para um PostgreSQL acessível localmente (`localhost`, não `db`).

## Rodando os testes

A suíte usa **SQLite em memória por padrão** — zero configuração, rápida e determinística. Cada teste recria o schema, e as chamadas de rede (feriados, SMTP) são mockadas, então nenhum e-mail real é enviado nem há dependência de serviços externos.

```bash
pip install -r requirements.txt
pytest                      # roda tudo com cobertura
pytest -m "not lento"       # pula os testes que treinam modelos de verdade (mais rápido)
```

- **Cobertura:** o `pytest.ini` já exige cobertura mínima de **75%** (`--cov-fail-under=75`); o relatório HTML fica em `htmlcov/`. O projeto tem mais de 230 testes e cobertura acima de 90%.
- **Marcador `lento`:** os poucos testes que treinam LightGBM/SARIMA de verdade são marcados com `@pytest.mark.lento`; a orquestração é testada com um estimador falso, mantendo a suíte rápida no dia a dia.
- **Fidelidade com Postgres:** para rodar contra um PostgreSQL real (como no CI), defina `TEST_DATABASE_URL` apontando para o banco desejado — o `conftest` detecta e usa esse banco no lugar do SQLite.

A suíte cobre o pipeline de importação, classificação ABC/XYZ, e-mail, autenticação e recuperação de senha, camada de consulta, o módulo de ML (features, métricas, elegibilidade, validação, treino e previsão), dashboard, exportação e rastreabilidade (logs).

## Integração contínua

O workflow em `.github/workflows/ci.yml` roda a suíte com cobertura a cada push/PR na `main` e falha se a cobertura ficar abaixo de 75%.
