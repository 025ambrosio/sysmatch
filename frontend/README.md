# Frontend

Interface web React/Vite do Conciliador NF x Etiquetas.

Este modulo e usado pela equipe operacional para enviar arquivos, processar lotes, baixar PDFs finais e verificar pendencias.

## Responsabilidades

- Exibir dashboard.
- Separar operacao por marketplace.
- Enviar arquivos para o backend.
- Mostrar resultado dos lotes.
- Baixar PDF final de impressao.
- Baixar relatorio Excel.
- Mostrar conciliados, pendentes e itens para revisar.

O frontend nao executa OCR nem gera PDF. Essas tarefas pertencem ao backend.

## Pre-Requisitos

- Node.js.
- NPM.
- Backend rodando na porta `8010`.

## Instalacao

```bat
cd frontend
npm install
```

## Execucao

```bat
cd frontend
npm run dev
```

Acesso local:

```text
http://localhost:8080
```

Acesso pela rede local:

```text
http://192.168.15.2:8080
```

## Conexao Com O Backend

O backend deve estar disponivel em:

```text
http://localhost:8010
```

ou, na rede local:

```text
http://192.168.15.2:8010
```

A URL padrao da API fica em:

```text
src/lib/api.ts
```

Se o IP do computador principal mudar, ajuste a URL da API ou use a tela de configuracoes, se disponivel.

## Comandos

Desenvolvimento:

```bat
npm run dev
```

Build:

```bat
npm run build
```

Preview do build:

```bat
npm run preview
```

## Arquivos Importantes

```text
src/
├── components/
├── hooks/
├── lib/
├── routes/
├── main.tsx
├── router.tsx
├── routeTree.gen.ts
└── styles.css
```

## Nao Versionar

- `node_modules/`
- `dist/`
- `.tanstack/`
- arquivos `.local`
- logs

Esses itens sao ignorados pelo Git.
