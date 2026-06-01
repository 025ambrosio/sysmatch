# Conciliador NF x Etiquetas

Sistema local/web para conciliar notas fiscais, DANFEs e etiquetas de marketplaces, gerando PDF final de impressao e relatorios de conferencia.

O objetivo e reduzir trabalho manual na logistica: o operador envia os arquivos em lote, o sistema cruza os dados e separa automaticamente itens conciliados, pendentes e para revisao.

> Este sistema nao emite nota fiscal. Ele apenas processa arquivos ja emitidos.

## Estrutura Do Projeto

```text
.
├── backend/    # API Python/FastAPI, OCR, matching, PDF e relatorios
└── frontend/   # Interface web React/Vite
```

## Componentes

### Backend

Responsavel por:

- leitura de PDFs/XMLs de NF-e ou DANFE;
- leitura de etiquetas em PDF, imagem, ZPL ou TXT;
- OCR com Tesseract;
- conciliacao NF x etiqueta;
- geracao de PDF final;
- geracao de relatorio CSV/Excel.

Porta padrao:

```text
http://localhost:8010
```

### Frontend

Interface usada pela equipe para:

- selecionar marketplace;
- enviar notas/DANFEs;
- enviar etiquetas;
- processar lotes;
- baixar PDF final;
- baixar relatorio;
- verificar pendencias.
- converter arquivos ZPL/TXT em PDF multipagina local.

Porta padrao:

```text
http://localhost:8080
```

## Pre-Requisitos

- Windows como ambiente principal.
- Python 3.11 ou superior.
- Node.js e NPM.
- Tesseract OCR.
- Git, caso va clonar o projeto.

O Tesseract OCR e procurado no caminho padrao:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Instalacao Inicial

### Backend

```bat
cd backend
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bat
cd frontend
npm install
```

## Rodar O Sistema

Abra dois terminais.

### Terminal 1 - Backend

```bat
cd backend
call .venv\Scripts\activate
uvicorn api:app --host 0.0.0.0 --port 8010
```

Documentacao da API:

```text
http://localhost:8010/docs
```

### Terminal 2 - Frontend

```bat
cd frontend
npm run dev
```

Acesso local:

```text
http://localhost:8080
```

## Acesso Pela Rede Local

O computador principal deve manter backend e frontend ligados.

Exemplo com IP local `192.168.15.2`:

```text
Frontend: http://192.168.15.2:8080
Backend:  http://192.168.15.2:8010
```

Nos outros computadores, a equipe acessa:

```text
http://192.168.15.2:8080
```

Se o IP mudar, atualize a URL da API no frontend ou configure novamente pela tela de configuracoes.

## Uso Operacional

1. Abrir o sistema no navegador.
2. Selecionar o marketplace.
3. Enviar arquivos de NF/DANFE.
4. Enviar arquivos de etiquetas.
5. Processar o lote.
6. Baixar o PDF final.
7. Baixar o relatorio Excel/CSV.
8. Conferir pendencias ou itens para revisar.

## Conversor ZPL Para PDF

O sistema tambem possui a tela `Conversor ZPL`, que recebe arquivos `.zpl` ou `.txt`, separa etiquetas por blocos `^XA ... ^XZ` e gera um PDF multipagina local, sem Labelary e sem servicos online.

Padrao inicial:

```text
100x150mm, 203 DPI
```

Endpoint principal:

```text
POST /api/zpl/convert
```

O PDF final fica em:

```text
backend/output/zpl_converter/
```

Mais detalhes: [Conversor ZPL Para PDF](./docs/CONVERSOR_ZPL_PDF.md)

## Arquivos Gerados

O backend gera arquivos em:

```text
backend/output/
```

Essa pasta recebe PDFs, relatorios e dados dos lotes durante o uso.

## Nao Enviar Para O GitHub

Os itens abaixo nao devem ser versionados:

- `.venv/`
- `node_modules/`
- `dist/`
- `output/` com arquivos reais;
- PDFs de nota;
- PDFs de etiqueta;
- relatorios gerados;
- caches como `__pycache__/`.

Esses itens estao cobertos pelo `.gitignore`.

## Parar O Sistema

Pressione `Ctrl + C` nos terminais do backend e do frontend.

## Problemas Comuns

### `python` nao e reconhecido

Instale o Python e marque `Add Python to PATH`.

### `npm` nao e reconhecido

Instale o Node.js.

### `uvicorn` nao e reconhecido

Ative o ambiente virtual e reinstale as dependencias:

```bat
cd backend
call .venv\Scripts\activate
pip install -r requirements.txt
```

### Tesseract OCR nao encontrado

Confira se existe:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Frontend abre, mas nao processa

Verifique se o backend esta ligado:

```text
http://localhost:8010/docs
```

### Outro computador nao acessa

Verifique:

- backend iniciado com `--host 0.0.0.0`;
- frontend iniciado com `--host 0.0.0.0`;
- firewall liberando portas `8010` e `8080`;
- IP correto do computador principal;
- computadores na mesma rede.

## Documentacao Por Modulo

- [Backend](./backend/README.md)
- [Frontend](./frontend/README.md)
- [Conversor ZPL Para PDF](./docs/CONVERSOR_ZPL_PDF.md)
