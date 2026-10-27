# MedStock-AI — Frontend

Interface web do MedStock-AI, em **Next.js (App Router) + TypeScript + Tailwind CSS**.

## Requisitos

- Node.js 18.18+ (ou 20+)
- Backend rodando (por padrão em `http://localhost:8000`)

## Configuração

```bash
cp .env.local.example .env.local   # ajuste NEXT_PUBLIC_API_URL se necessário
npm install
```

## Desenvolvimento

```bash
npm run dev
```

Acesse http://localhost:3000. A home mostra o status de conexão com o backend.

> O CORS do backend libera `http://localhost:3000` (variável `FRONTEND_URL`).

## Scripts

| Script          | O que faz                         |
| --------------- | --------------------------------- |
| `npm run dev`   | Servidor de desenvolvimento       |
| `npm run build` | Build de produção                 |
| `npm run start` | Sobe o build de produção          |
| `npm run lint`  | Lint (ESLint + regras do Next)    |

## Estrutura

```
src/
  app/            Rotas (App Router): layout, páginas, estilos globais
  components/     Componentes de UI
  lib/
    api.ts        Cliente HTTP da API (token JWT + helpers)
```

As telas serão implementadas a partir do design **Previa Insumos**.
