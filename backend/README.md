# Backend

API Python/FastAPI do Conciliador NF x Etiquetas.

Este modulo executa o processamento principal do sistema: leitura de arquivos, OCR, conciliacao, geracao de PDFs finais e relatorios.

> O backend nao emite nota fiscal. Ele apenas processa arquivos ja emitidos.

## Responsabilidades

- Receber arquivos enviados pelo frontend.
- Ler NF-e em XML.
- Ler DANFE/NF em PDF.
- Ler etiquetas em PDF, imagem, ZPL ou TXT.
- Executar OCR quando necessario.
- Comparar NF x etiqueta.
- Gerar PDF final de impressao.
- Gerar PDFs individuais, quando disponivel.
- Gerar relatorios CSV/Excel.
- Converter arquivos ZPL/TXT em PDF multipagina local.
- Salvar resultados em `output/`.

## Arquivos Aceitos

Notas/DANFEs:

- `.pdf`
- `.xml`

Etiquetas:

- `.pdf`
- imagens suportadas pela Pillow;
- `.zpl`
- `.txt`

## Pre-Requisitos

- Python 3.11 ou superior.
- Tesseract OCR instalado.
- Dependencias listadas em `requirements.txt`.

Caminho padrao do Tesseract no Windows:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Instalacao

```bat
cd backend
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
```

## Execucao

```bat
cd backend
call .venv\Scripts\activate
uvicorn api:app --host 0.0.0.0 --port 8010
```

API:

```text
http://localhost:8010
```

Documentacao automatica:

```text
http://localhost:8010/docs
```

## Endpoints

Health check:

```text
GET /api/health
```

Marketplaces:

```text
GET /api/marketplaces
```

Processar lote:

```text
POST /api/processar-lote
```

Listar lotes:

```text
GET /api/lotes
GET /api/lotes?marketplace=Shopee
```

Detalhar lote:

```text
GET /api/lotes/{job_id}
```

Downloads:

```text
GET /api/lotes/{job_id}/arquivos/pdf_final
GET /api/lotes/{job_id}/arquivos/relatorio_excel
GET /api/lotes/{job_id}/arquivos/zip_individuais
```

Conversor ZPL para PDF:

```text
POST /api/zpl/convert
GET /api/zpl/{job_id}/pdf
GET /api/zpl/{job_id}/relatorio
```

O endpoint aceita arquivos `.zpl` ou `.txt`, separa as etiquetas por blocos `^XA ... ^XZ` e gera um PDF local em `output/zpl_converter/`.

## Saidas

Arquivos gerados ficam em:

```text
output/
```

Estrutura:

```text
output/
├── api_jobs/
├── conciliados/
├── pendentes/
├── relatorios/
└── revisar/
```

Essas pastas ficam vazias no GitHub e recebem arquivos durante a execucao.

## Conciliacao Em Alto Nivel

O backend prioriza:

1. Numero da NF.
2. Chave NF-e.
3. CNPJ emitente, quando disponivel.
4. CEP, nome, endereco e cidade como apoio.

Itens com dados fortes sao conciliados automaticamente. Itens com dados incompletos podem ir para revisao.

## Problemas Comuns

### Tesseract nao encontrado

Verifique se o arquivo existe:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

### OCR fraco ou incompleto

Pode ocorrer com PDFs comprimidos, imagens pequenas, texto perto de codigo de barras ou arquivos com baixa resolucao.

### Porta 8010 em uso

Feche o processo antigo ou escolha outra porta. Se mudar a porta, atualize tambem o frontend.

## Conversor ZPL Para PDF

O modulo `services/zpl_converter/` converte lotes ZPL localmente, sem Labelary. A primeira versao renderiza textos, linhas/caixas e Code 128. Comandos graficos como `^GF`, imagens externas e alguns codigos 2D tem suporte limitado e aparecem como avisos no relatorio.

Documentacao completa: `docs/CONVERSOR_ZPL_PDF.md`.
