# MedStock AI — Backend

API de análise preditiva de consumo de insumos hospitalares, construída com FastAPI + SQLAlchemy + PostgreSQL.

## Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** (ORM) + **PostgreSQL**
- **JWT** (`python-jose`) para autenticação
- **bcrypt** para hash de senha
- Pandas / NumPy / LightGBM / statsmodels / skforecast — pipeline de dados e previsão (em desenvolvimento)

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (forma recomendada de rodar o projeto)
- Python 3.14 (só necessário se for rodar sem Docker)

## Configuração (`.env`)

Crie um arquivo `.env` na raiz do `Backend/` com as seguintes variáveis:

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | String de conexão do PostgreSQL (ex: `postgresql+psycopg://postgres:SENHA@localhost:5432/medstock`) |
| `SECRET_KEY` | Chave usada para assinar os tokens JWT |
| `ALGORITHM` | Algoritmo do JWT (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do token de login, em minutos (default `60`) |
| `DEFINIR_SENHA_TOKEN_EXPIRE_MINUTES` | Validade do link de definição de senha, em minutos (default `2880` = 48h) |
| `FRONTEND_URL` | URL base do frontend, usada para montar o link enviado por e-mail (default `http://localhost:3000`) |
| `SUPER_ADMIN_EMAIL` | E-mail do super admin criado automaticamente no primeiro start |
| `SUPER_ADMIN_SENHA` | Senha do super admin criado automaticamente no primeiro start |
| `EMAIL_REMETENTE` | E-mail usado para enviar as notificações (ex: Gmail) |
| `SENHA_EMAIL` | Senha de app do e-mail remetente (no Gmail, precisa ser uma [senha de app](https://myaccount.google.com/apppasswords), não a senha normal da conta) |
| `SMTP_HOST` / `SMTP_PORT` | Servidor SMTP (default `smtp.gmail.com:587`) |
| `FERIADOSAPI_KEY` | Chave da API de feriados usada no pipeline de dados |
| `POSTGRES_PASSWORD` | Senha do usuário `postgres` — usada pelo `docker-compose.yml` para subir o container do banco (deve ser a mesma senha usada em `DATABASE_URL`) |

O `.env` nunca deve ser commitado (já está no `.gitignore`).

## Rodando com Docker (recomendado)

Com o Docker Desktop aberto e o `.env` configurado:

```bash
docker compose up --build -d
```

Isso sobe dois serviços:
- **`db`**: PostgreSQL 16, com os dados persistidos em um volume nomeado (`postgres_data`).
- **`api`**: build da aplicação FastAPI, na porta `8000`.

No primeiro start, a aplicação cria automaticamente todas as tabelas e o usuário super admin (a partir de `SUPER_ADMIN_EMAIL`/`SUPER_ADMIN_SENHA`).

Verifique se subiu corretamente:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Documentação interativa (Swagger): http://localhost:8000/docs

### Comandos úteis

| Comando | Efeito |
|---|---|
| `docker compose up -d` | Sobe os serviços (sem rebuildar a imagem) |
| `docker compose up --build -d` | Rebuilda a imagem da API e sobe os serviços — use depois de mudar `requirements.txt` ou o `Dockerfile` |
| `docker compose logs -f api` | Acompanha os logs da API em tempo real |
| `docker compose down` | Para os containers (mantém os dados do banco) |
| `docker compose down -v` | Para os containers **e apaga os dados do banco** (reset completo) |

> **Atenção**: como o projeto ainda não usa Alembic, o schema do banco é criado via `Base.metadata.create_all()` no startup — isso só cria tabelas que não existem, nunca altera tabelas já existentes. Se você mudar um modelo (nova coluna, etc.), é necessário resetar o banco (`docker compose down -v` seguido de `docker compose up -d`) para o schema novo ser aplicado.

## Rodando sem Docker

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Nesse caso, `DATABASE_URL` no `.env` deve apontar para um PostgreSQL acessível localmente (`localhost`, não `db`).
