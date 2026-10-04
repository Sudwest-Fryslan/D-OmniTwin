"""
Catalogusweergave (DCAT-AP-NL, JSON-LD) van de geregistreerde datasets
======================================================================
Besluit RFC § 9 punt 14: eerst een JSON-LD-weergave van `GET /api/laden/v1/datasets`
(`Accept: application/ld+json`); een eigen `catalogus/v1` pas bij een tweede bron van metadata.

Per dataset de beschrijving uit de registratie (DCAT-AP-NL/GeoDCAT-AP), aangevuld met
`dct:identifier`, `dct:conformsTo` (het profiel) en, na een publicatie, `dct:modified` en
`dcat:distribution` (het geleverde bestand van de actuele versie).
"""

from __future__ import annotations

from omnitwin.laden.profielen import profiel_uri

BASIS = "/api/laden/v1"
CONTEXT = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "spdx": "http://spdx.org/rdf/terms#",
}
PUBLIEK = "http://publications.europa.eu/resource/authority/access-right/PUBLIC"


def is_publiek(beschrijving: dict) -> bool:
    w = (beschrijving or {}).get("dct:accessRights")
    if isinstance(w, dict):
        w = w.get("@id")
    return str(w or "").rstrip("/") == PUBLIEK


def toegang_van(beschrijving: dict) -> str:
    """openbaar (dct:accessRights PUBLIC) of intern (al het andere, ook ontbrekend), #254. Zelfde regel
    als laden.toegang_uit_dcat in de database (V032)."""
    return "openbaar" if is_publiek(beschrijving) else "intern"


def distributie(dataset_id: str, versie: int, levering: dict) -> dict:
    return {
        "@type": "dcat:Distribution",
        "dcat:accessURL": f"{BASIS}/datasets/{dataset_id}/versies/{versie}/bestand",
        "dcat:mediaType": levering.get("mediatype"),
        "dcat:byteSize": levering.get("grootte"),
        "spdx:checksum": {"@type": "spdx:Checksum", "spdx:algorithm": "spdx:checksumAlgorithm_sha256",
                          "spdx:checksumValue": levering.get("sha256")},
    }


def dataset_jsonld(ds: dict, basis_url: str = "") -> dict:
    besch = {k: v for k, v in (ds.get("beschrijving") or {}).items() if k != "@context"}
    besch.setdefault("@type", "dcat:Dataset")
    besch["@id"] = f"{basis_url}{BASIS}/datasets/{ds['id']}"
    besch["dct:identifier"] = ds["id"]
    eigen = besch.get("dct:conformsTo")
    profiel = profiel_uri(ds["profiel"])
    besch["dct:conformsTo"] = [profiel] + ([eigen] if eigen and eigen != profiel else [])
    return besch


def catalogus(datasets: list[dict], basis_url: str = "") -> dict:
    return {
        "@context": CONTEXT,
        "@id": f"{basis_url}{BASIS}/datasets",
        "@type": "dcat:Catalog",
        "dct:title": "D-OmniTwin — geregistreerde datasets",
        "dct:description": "Datasets die via de laad-API in deze installatie van D-OmniTwin worden geladen.",
        "dcat:dataset": [dataset_jsonld(d, basis_url) for d in datasets],
    }
