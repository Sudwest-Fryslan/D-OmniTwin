"""
Een levering lezen
==================
Van het ruw bewaarde bestand naar resources met regels, los van het profiel:

| Mediatype | Wordt |
|---|---|
| `text/csv` | één resource (de enige van het profiel, bijv. `waarnemingen`) |
| `application/json` | array → de enige resource; object → resource per sleutel (bijv. definities-adapter) |
| `application/zip` | Data Package: `datapackage.json` met CSV- of GeoPackage-resources, optioneel `dcat.jsonld` |
| `application/geopackage+sqlite3` | tabellen (zonder geometrie) als resources; featuretabellen via fiona (`features`) |

Regelnummer 1 = de eerste dataregel na de kop (zoals `Probleem.regel` in de specificatie).
Een bestand dat niet te lezen is, geeft `Onleesbaar` (code formaat-ongeldig).
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator

csv.field_size_limit(10 * 1024 * 1024)

ZIP = "application/zip"
GPKG = "application/geopackage+sqlite3"
CSV = "text/csv"
JSON = "application/json"
MEDIATYPES = (GPKG, ZIP, CSV, JSON)
MAX_UITGEPAKT_FACTOR = 20  # zip-bom: uitgepakt hoogstens 20 × de limiet


class Onleesbaar(ValueError):
    """Het bestand is geen geldige zip, Data Package, GeoPackage, CSV of JSON."""


@dataclass
class Resource:
    naam: str
    kop: list[str] | None            # kolommen (CSV, GeoPackage-tabel); None bij JSON
    regels: list[dict] = field(default_factory=list)


@dataclass
class Bron:
    resources: dict[str, Resource] = field(default_factory=dict)
    gpkg: Path | None = None          # GeoPackage (los of uit de zip), voor featuretabellen
    dcat: dict | None = None          # dcat.jsonld uit de zip
    json: object = None               # de geparste JSON-body (voor adapters)
    tijdelijk: tempfile.TemporaryDirectory | None = None

    def sluit(self):
        if self.tijdelijk:
            self.tijdelijk.cleanup()


def kale_mediatype(mt: str | None) -> str:
    return (mt or "").split(";")[0].strip().lower()


def _csv(tekst_bytes: bytes, naam: str) -> Resource:
    try:
        tekst = tekst_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Onleesbaar(f"{naam}: geen UTF-8")
    lezer = csv.reader(io.StringIO(tekst, newline=""))
    try:
        kop = next(lezer)
    except StopIteration:
        raise Onleesbaar(f"{naam}: leeg bestand, geen kopregel")
    except csv.Error as e:
        raise Onleesbaar(f"{naam}: geen geldige CSV ({e})")
    kop = [k.strip() for k in kop]
    if len(set(kop)) != len(kop):
        raise Onleesbaar(f"{naam}: dubbele kolomnamen in de kopregel")
    regels = []
    try:
        for rij in lezer:
            if not rij or (len(rij) == 1 and rij[0] == ""):
                continue
            if len(rij) != len(kop):
                raise Onleesbaar(f"{naam}: regel {len(regels) + 1} heeft {len(rij)} kolommen, de kop {len(kop)}")
            regels.append(dict(zip(kop, rij)))
    except csv.Error as e:
        raise Onleesbaar(f"{naam}: geen geldige CSV ({e})")
    return Resource(naam, kop, regels)


def _gpkg_tabellen(pad: Path) -> dict[str, Resource]:
    """Tabellen zonder geometrie (data_type 'attributes') uit een GeoPackage, via sqlite3."""
    try:
        con = sqlite3.connect(f"file:{pad}?mode=ro", uri=True)
    except sqlite3.Error as e:
        raise Onleesbaar(f"GeoPackage niet te openen ({e})")
    try:
        con.row_factory = sqlite3.Row
        try:
            inhoud = con.execute("SELECT table_name, data_type FROM gpkg_contents").fetchall()
        except sqlite3.DatabaseError:
            raise Onleesbaar("geen GeoPackage (tabel gpkg_contents ontbreekt)")
        uit = {}
        for r in inhoud:
            if r["data_type"] != "attributes":
                continue
            naam = r["table_name"]
            cur = con.execute(f'SELECT * FROM "{naam.replace(chr(34), "")}"')
            kop = [d[0] for d in cur.description if d[0] != "fid"]  # fid: primaire sleutel van GDAL
            regels = [{k: rij[k] for k in kop} for rij in cur.fetchall()]
            uit[naam] = Resource(naam, kop, regels)
        return uit
    finally:
        con.close()


def gpkg_lagen(pad: Path) -> dict[str, str]:
    """{tabel: data_type} uit gpkg_contents."""
    try:
        con = sqlite3.connect(f"file:{pad}?mode=ro", uri=True)
        try:
            return {t: d for t, d in con.execute("SELECT table_name, data_type FROM gpkg_contents")}
        finally:
            con.close()
    except sqlite3.Error:
        raise Onleesbaar("geen GeoPackage (tabel gpkg_contents ontbreekt)")


def _veilige_naam(naam: str) -> bool:
    p = PurePosixPath(naam)
    return not p.is_absolute() and ".." not in p.parts and "\\" not in naam


def _zip(pad: Path, max_bytes: int, bron: Bron) -> None:
    try:
        z = zipfile.ZipFile(pad)
    except zipfile.BadZipFile:
        raise Onleesbaar("geen geldige zip")
    with z:
        namen = {i.filename: i for i in z.infolist() if not i.is_dir()}
        if sum(i.file_size for i in namen.values()) > max_bytes * MAX_UITGEPAKT_FACTOR:
            raise Onleesbaar("uitgepakt te groot")
        if "datapackage.json" not in namen:
            raise Onleesbaar("datapackage.json ontbreekt in de root van de zip")
        try:
            dp = json.loads(z.read("datapackage.json").decode("utf-8-sig"))
            resources = dp["resources"]
            assert isinstance(resources, list)
        except (ValueError, KeyError, AssertionError, UnicodeDecodeError):
            raise Onleesbaar("datapackage.json is geen geldig Data Package (resources ontbreken)")
        if "dcat.jsonld" in namen:
            try:
                d = json.loads(z.read("dcat.jsonld").decode("utf-8-sig"))
                bron.dcat = d if isinstance(d, dict) else None
            except (ValueError, UnicodeDecodeError):
                raise Onleesbaar("dcat.jsonld is geen geldige JSON")
        for r in resources:
            naam, rpad = r.get("name"), r.get("path")
            if not isinstance(naam, str) or not isinstance(rpad, str) or not _veilige_naam(rpad):
                raise Onleesbaar("resource zonder geldige name of path")
            if rpad not in namen:
                raise Onleesbaar(f"resource {naam}: {rpad} ontbreekt in de zip")
            if rpad.lower().endswith(".gpkg") or r.get("format") == "gpkg":
                bron.tijdelijk = bron.tijdelijk or tempfile.TemporaryDirectory(prefix="levering-")
                doel = Path(bron.tijdelijk.name) / f"{len(bron.resources)}.gpkg"
                with z.open(rpad) as src, open(doel, "wb") as dst:
                    while True:
                        blok = src.read(1024 * 1024)
                        if not blok:
                            break
                        dst.write(blok)
                bron.gpkg = doel
                for tnaam, res in _gpkg_tabellen(doel).items():
                    bron.resources.setdefault(tnaam, res)
            else:
                if r.get("format", "csv") != "csv" and not rpad.lower().endswith(".csv"):
                    raise Onleesbaar(f"resource {naam}: alleen CSV of GeoPackage")
                bron.resources[naam] = _csv(z.read(rpad), naam)


def lees(pad: Path, mediatype: str, enige_resource: str | None, max_bytes: int) -> Bron:
    """Lees de levering. enige_resource: naam voor een CSV of JSON-array (profiel met één resource)."""
    mt = kale_mediatype(mediatype)
    bron = Bron()
    try:
        if mt == CSV:
            bron.resources[enige_resource or "data"] = _csv(Path(pad).read_bytes(), enige_resource or "data")
        elif mt == JSON:
            try:
                data = json.loads(Path(pad).read_bytes().decode("utf-8-sig"))
            except (ValueError, UnicodeDecodeError):
                raise Onleesbaar("geen geldige JSON (UTF-8)")
            bron.json = data
            if isinstance(data, list):
                if not all(isinstance(r, dict) for r in data):
                    raise Onleesbaar("JSON-array met elementen die geen object zijn")
                bron.resources[enige_resource or "data"] = Resource(enige_resource or "data", None, data)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list) and all(isinstance(r, dict) for r in v):
                        bron.resources[k] = Resource(k, None, v)
            else:
                raise Onleesbaar("JSON moet een array of een object zijn")
        elif mt == ZIP:
            _zip(Path(pad), max_bytes, bron)
        elif mt == GPKG:
            bron.gpkg = Path(pad)
            bron.resources.update(_gpkg_tabellen(Path(pad)))
        else:
            raise Onleesbaar(f"mediatype {mt} wordt niet gelezen")
    except Exception:
        bron.sluit()
        raise
    return bron


def regels(res: Resource) -> Iterator[tuple[int, dict]]:
    for i, r in enumerate(res.regels, start=1):
        yield i, r
