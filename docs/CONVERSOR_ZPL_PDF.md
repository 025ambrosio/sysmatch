# Conversor ZPL Para PDF

Modulo local para converter arquivos `.zpl` ou `.txt` em PDF multipagina, sem Labelary e sem servicos online.

## Como Usar Pelo Frontend

1. Abra o frontend em `http://localhost:8080`.
2. Acesse `Conversor ZPL` no menu lateral.
3. Envie um arquivo `.zpl` ou `.txt`.
4. Ajuste marketplace, tamanho da etiqueta e DPI, se necessario.
5. Clique em `Converter`.
6. Baixe o PDF final quando o processamento terminar.

Padrao inicial:

```text
largura: 100 mm
altura: 150 mm
dpi: 203
```

## API

Converter:

```text
POST /api/zpl/convert
```

Campos `multipart/form-data`:

- `file`: arquivo `.zpl` ou `.txt`.
- `marketplace`: opcional.
- `width_mm`: opcional, padrao `100`.
- `height_mm`: opcional, padrao `150`.
- `dpi`: opcional, padrao `203`.
- `batch_name`: opcional.

Download do PDF:

```text
GET /api/zpl/{job_id}/pdf
```

Relatorio:

```text
GET /api/zpl/{job_id}/relatorio
```

## Saida

Os arquivos sao salvos em:

```text
backend/output/zpl_converter/{job_id}/
```

Arquivos gerados:

- `etiquetas_convertidas.pdf`
- `relatorio.json`

## Limitacoes Conhecidas

Esta primeira versao e um renderizador local focado nos ZPLs comuns da operacao. Ela separa etiquetas por blocos `^XA ... ^XZ` e renderiza:

- textos com `^FO`/`^FT`, `^A`, `^FD`, `^FS`;
- caixas e linhas com `^GB`;
- codigo de barras Code 128 com `^BY`, `^BC`, `^FD`.

Comandos graficos e codigos 2D como `^GF`, `^XG`, `^BQ`, `^BX` ainda tem suporte limitado. Quando aparecerem, o sistema registra aviso ou falha apenas a etiqueta afetada, mantendo o lote em processamento.

## Testes

No backend:

```bat
cd backend
pytest
```
