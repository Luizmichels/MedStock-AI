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

## Rodando os testes

Os testes rodam contra um PostgreSQL de verdade (não um banco simulado), em um banco separado (`medstock_test`) dentro do mesmo Postgres do `docker-compose.yml` — assim eles validam de verdade a conexão, a criação das tabelas e as constraints (`NOT NULL`, `unique`), sem tocar no banco de desenvolvimento.

```bash
docker compose up -d db     # garante que o Postgres está disponível em localhost:5432
pip install -r requirements.txt
pytest -v
```

O banco `medstock_test` é criado automaticamente na primeira execução, e cada teste roda dentro de uma transação que é desfeita (`rollback`) ao final — então rodar a suíte várias vezes seguidas não deixa dados residuais nem exige resetar o banco manualmente. Os e-mails de aprovação de solicitação são interceptados (mock) durante os testes, então nenhum e-mail real é enviado.

Cobertura atual ([tests/](tests/)):
- `test_database.py` — conexão com o banco, criação de todas as tabelas, e as constraints que já causaram bugs antes (`endereco` `NOT NULL`, `email` único).
- `test_auth.py` — login (sucesso, senha errada, usuário inativo) e o fluxo de `/auth/definir-senha` (incluindo o link não poder ser reutilizado).
- `test_empresas.py` — envio de solicitação (validação), permissões de super admin, e o fluxo completo de aprovação (cria empresa + usuário admin + dispara e-mail).
- `test_usuarios.py` — permissões de admin, isolamento de dados entre empresas diferentes, e-mail duplicado, desativação.