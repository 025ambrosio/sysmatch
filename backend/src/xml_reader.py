from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .utils import normalize_cep, only_digits


NFE_NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def _text(root: ET.Element, path: str) -> str:
    node = root.find(path, NFE_NS)
    return (node.text or "").strip() if node is not None else ""


def _find_inf_nfe(root: ET.Element) -> ET.Element:
    inf = root.find(".//nfe:infNFe", NFE_NS)
    if inf is None:
        inf = root.find(".//infNFe")
    if inf is None:
        raise ValueError("Tag infNFe nao encontrada no XML.")
    return inf


def _inf_id_to_key(inf_nfe: ET.Element) -> str:
    raw_id = inf_nfe.attrib.get("Id", "")
    return raw_id[3:] if raw_id.startswith("NFe") else raw_id


def _find_all_inf_nfe(root: ET.Element) -> list[ET.Element]:
    infs = root.findall(".//nfe:infNFe", NFE_NS)
    if not infs:
        infs = root.findall(".//infNFe")
    return infs


def _find_protocol_for_key(root: ET.Element, chave: str) -> ET.Element | None:
    inf_prots = root.findall(".//nfe:protNFe/nfe:infProt", NFE_NS) or root.findall(".//infProt")
    for inf_prot in inf_prots:
        if _text(inf_prot, "nfe:chNFe") == chave or _text(inf_prot, "chNFe") == chave:
            return inf_prot
    return inf_prots[0] if len(inf_prots) == 1 else None


def _products(root: ET.Element) -> list[dict]:
    items = []
    det_nodes = root.findall(".//nfe:det", NFE_NS) or root.findall(".//det")
    for det in det_nodes:
        prod = det.find("nfe:prod", NFE_NS) or det.find("prod")
        if prod is None:
            continue
        get = lambda tag: _text(prod, f"nfe:{tag}") or _text(prod, tag)
        items.append(
            {
                "codigo": get("cProd"),
                "ean": get("cEAN"),
                "descricao": get("xProd"),
                "ncm": get("NCM"),
                "quantidade": get("qCom"),
                "valor_unitario": get("vUnCom"),
                "valor_total": get("vProd"),
            }
        )
    return items


def _parse_inf_nfe(inf_nfe: ET.Element, document_root: ET.Element, path: Path, index: int, total: int) -> dict:
    chave = _inf_id_to_key(inf_nfe)
    protocol = _find_protocol_for_key(document_root, chave)
    if protocol is not None:
        chave = _text(protocol, "nfe:chNFe") or _text(protocol, "chNFe") or chave

    status = ""
    motivo = ""
    if protocol is not None:
        status = _text(protocol, "nfe:cStat") or _text(protocol, "cStat")
        motivo = _text(protocol, "nfe:xMotivo") or _text(protocol, "xMotivo")

    logradouro = _text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:xLgr")
    numero = _text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:nro")
    bairro = _text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:xBairro")
    cidade = _text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:xMun")
    uf = _text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:UF")
    cep = normalize_cep(_text(inf_nfe, ".//nfe:dest/nfe:enderDest/nfe:CEP"))
    numero_nf = _text(inf_nfe, ".//nfe:ide/nfe:nNF")
    source_file = path.name if total == 1 else f"{path.name} - NF {numero_nf or index}"

    return {
        "numero_nf": numero_nf,
        "serie": _text(inf_nfe, ".//nfe:ide/nfe:serie"),
        "chave_nfe": chave,
        "data_emissao": _text(inf_nfe, ".//nfe:ide/nfe:dhEmi"),
        "emitente_nome": _text(inf_nfe, ".//nfe:emit/nfe:xNome"),
        "emitente_documento": only_digits(
            _text(inf_nfe, ".//nfe:emit/nfe:CNPJ") or _text(inf_nfe, ".//nfe:emit/nfe:CPF")
        ),
        "destinatario_nome": _text(inf_nfe, ".//nfe:dest/nfe:xNome"),
        "destinatario_documento": only_digits(
            _text(inf_nfe, ".//nfe:dest/nfe:CPF") or _text(inf_nfe, ".//nfe:dest/nfe:CNPJ")
        ),
        "destinatario_email": _text(inf_nfe, ".//nfe:dest/nfe:email"),
        "destinatario_logradouro": logradouro,
        "destinatario_numero": numero,
        "destinatario_bairro": bairro,
        "destinatario_cidade": cidade,
        "destinatario_uf": uf,
        "destinatario_cep": cep,
        "destinatario_endereco": " ".join(part for part in [logradouro, numero, bairro, cidade, uf, cep] if part),
        "produtos": _products(inf_nfe),
        "valor_total_nf": _text(inf_nfe, ".//nfe:total/nfe:ICMSTot/nfe:vNF"),
        "status_autorizacao": status,
        "motivo_autorizacao": motivo,
        "autorizada": status == "100",
        "source_file": source_file,
        "source_path": str(path),
        "source_index": index,
    }


def parse_nfe_xmls(file: str | Path) -> list[dict]:
    path = Path(file)
    tree = ET.parse(path)
    root = tree.getroot()
    infs = _find_all_inf_nfe(root)
    if not infs:
        raise ValueError("Tag infNFe nao encontrada no XML.")

    total = len(infs)
    nfes = [_parse_inf_nfe(inf, root, path, index, total) for index, inf in enumerate(infs, start=1)]
    print(f"[XML] arquivo={path.name} nfes_encontradas={len(nfes)} numeros={[nfe.get('numero_nf') for nfe in nfes]}")
    return nfes


def parse_nfe_xml(file: str | Path) -> dict:
    return parse_nfe_xmls(file)[0]
