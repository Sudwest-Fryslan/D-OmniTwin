"""
Bewijs per use case (#225): bewijsstappen in de manifesten, het compacte bewijs in git
(≤ 150 KB per afbeelding, ≤ 4 per use case, bewijs.json geldig) en de galerij in de
root-README actueel. Geen stack, geen browser.
"""

import io
import json

import pytest

from omnitwin import usecase_bewijs as ub
from omnitwin import usecases as uc
from omnitwin.laden.registratie import valideer

pytestmark = pytest.mark.unit

ALLE = uc.lees_usecases()
ACTIEF = {n: u for n, u in ALLE.items() if u.get("status") == "actief"}
BEWIJS_SCHEMA = json.loads(ub.BEWIJS_SCHEMA.read_text(encoding="utf-8"))
BEWIJSMAPPEN = sorted(p for p in ub.USECASES_DIR.glob("*/bewijs") if p.is_dir())


# ---------------------------------------------------------------- manifesten


@pytest.mark.parametrize("naam", sorted(ACTIEF))
def test_actieve_use_case_heeft_twee_tot_vier_bewijsstappen(naam):
    stappen = ub.stappen(ACTIEF[naam])
    assert 2 <= len(stappen) <= ub.MAX_STAPPEN, f"{naam}: {len(stappen)} bewijsstappen (2 tot 4)"
    ids = [s["id"] for s in stappen]
    assert len(ids) == len(set(ids)), f"{naam}: dubbele stap-id's {ids}"
    datasets = {d["id"] for d in ACTIEF[naam].get("datasets", [])}
    for s in stappen:
        if s["actie"] == "levering":
            assert s["dataset"] in datasets, f"{naam}/{s['id']}: dataset {s['dataset']} niet in datasets[]"
        if s["actie"] == "chat":
            assert s.get("vraag"), f"{naam}/{s['id']}: chat zonder vraag"
        if s["actie"] in ("open", "beheer"):
            assert s.get("pad"), f"{naam}/{s['id']}: {s['actie']} zonder pad"


# ---------------------------------------------------------------- compact bewijs in git


@pytest.mark.parametrize("map_", BEWIJSMAPPEN, ids=lambda p: p.parent.name)
def test_afbeeldingen_klein_en_hooguit_vier(map_):
    afbeeldingen = sorted(map_.glob("*.webp"))
    assert len(afbeeldingen) <= ub.MAX_STAPPEN, f"{map_.parent.name}: {len(afbeeldingen)} afbeeldingen (max 4)"
    for p in afbeeldingen:
        assert p.stat().st_size <= ub.MAX_BYTES, f"{p}: {p.stat().st_size} bytes (max {ub.MAX_BYTES})"
    for p in map_.glob("*"):  # alleen WebP; PNG/JPG horen in volledig/ (niet in git)
        assert p.is_dir() or p.suffix in (".webp", ".json", ".md"), f"{p}: alleen .webp, bewijs.json en README.md"


@pytest.mark.parametrize("map_", [m for m in BEWIJSMAPPEN if (m / "bewijs.json").exists()], ids=lambda p: p.parent.name)
def test_bewijsverslag_geldig_en_bij_het_manifest(map_):
    naam = map_.parent.name
    verslag = json.loads((map_ / "bewijs.json").read_text(encoding="utf-8"))
    assert valideer(verslag, BEWIJS_SCHEMA, BEWIJS_SCHEMA) == []
    assert verslag["naam"] == naam
    ids = [s["id"] for s in ub.stappen(ALLE[naam])]
    for s in verslag["stappen"]:
        assert s["id"] in ids, f"{naam}: stap {s['id']} staat niet (meer) in bewijs.stappen"
        assert (map_ / s["afbeelding"]).exists(), f"{naam}: {s['afbeelding']} ontbreekt"
    assert {p.stem for p in map_.glob("*.webp")} <= set(ids), f"{naam}: afbeelding zonder stap"
    tekst = json.dumps(verslag)
    assert "http://" not in tekst and "https://" not in tekst, f"{naam}: geen hostnamen in het verslag"


def test_galerij_en_readmes_actueel():
    assert ub.werk_galerij_bij(ALLE, controleer=True), "python -m omnitwin.usecases galerij"


# ---------------------------------------------------------------- functies


def test_gemeentecode():
    assert ub.gemeentecode("BU19000002") == "1900"
    assert ub.gemeentecode("WK190000") == "1900"
    assert ub.gemeentecode("GM0080") == "0080"
    assert ub.gemeentecode(None) == ""


def test_comprimeren_tot_onder_de_grens(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    import random

    rnd = random.Random(1)
    beeld = Image.new("RGB", (1440, 860))
    beeld.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)) for _ in range(1440 * 860)])
    buf = io.BytesIO()
    beeld.save(buf, "PNG")
    doel = tmp_path / "ruis.webp"
    grootte = ub.comprimeer(buf.getvalue(), doel)
    assert grootte == doel.stat().st_size <= ub.MAX_BYTES
    assert Image.open(doel).format == "WEBP"


def _fixture(tmp_path, crlf=False, met_bewijs=True):
    map_ = tmp_path / "usecases"
    (map_ / "x" / "bewijs").mkdir(parents=True)
    u = {
        "naam": "x",
        "titel": "Titel X",
        "vraag": "Hoe | waar?",
        "status": "actief",
        "versie": "1.0.0",
        "bewijs": {
            "stappen": [
                {"id": "kaart", "actie": "kaart", "omschrijving": "De kaart"},
                {"id": "chat", "actie": "chat", "vraag": "v"},
            ]
        },
    }
    readme = "# X\n\n## Bewijs\n\nOude tekst, niet in git.\n\n## Bekende afwijkingen\n\n- geen\n"
    (map_ / "x" / "README.md").write_bytes((readme.replace("\n", "\r\n") if crlf else readme).encode())
    if met_bewijs:
        (map_ / "x" / "bewijs" / "kaart.webp").write_bytes(b"RIFF")
        (map_ / "x" / "bewijs" / "chat.webp").write_bytes(b"RIFF")
        (map_ / "x" / "bewijs" / "bewijs.json").write_text(
            json.dumps(
                {
                    "specificatie": "1.0",
                    "naam": "x",
                    "versie": "1.0.0",
                    "omnitwin_versie": "0.3.0",
                    "datum": "2026-10-03T10:00:00+02:00",
                    "geslaagd": True,
                    "controles": [],
                    "stappen": [
                        {"id": "kaart", "resultaat": "ok", "afbeelding": "kaart.webp"},
                        {"id": "chat", "resultaat": "ok", "afbeelding": "chat.webp"},
                    ],
                }
            )
        )
    root = tmp_path / "README.md"
    root.write_text(f"# R\n\n{ub.GALERIJ_START}\n{ub.GALERIJ_EINDE}\n\nrest\n", encoding="utf-8")
    return map_, root, {"x": u}


def test_galerij_en_readme_blok(tmp_path):
    map_, root, ucs = _fixture(tmp_path, crlf=True)
    assert not ub.werk_galerij_bij(ucs, controleer=True, readme=root, map_=map_)
    assert ub.werk_galerij_bij(ucs, readme=root, map_=map_)
    assert ub.werk_galerij_bij(ucs, controleer=True, readme=root, map_=map_), "tweede keer actueel"
    galerij = root.read_text(encoding="utf-8")
    assert '<img src="usecases/x/bewijs/kaart.webp" width="320" alt="De kaart">' in galerij
    assert "**[Titel X](usecases/x/README.md)**<br>Hoe \\| waar?" in galerij
    assert galerij.endswith("\n\nrest\n")
    ruw = (map_ / "x" / "README.md").read_bytes().decode()
    assert "\r\n" in ruw and "\n" not in ruw.replace("\r\n", ""), "regeleinden van de README blijven CRLF"
    tekst = ruw.replace("\r\n", "\n")
    assert "Oude tekst" not in tekst
    assert "![De kaart](bewijs/kaart.webp)\n*De kaart*" in tekst and "![chat](bewijs/chat.webp)" in tekst
    assert tekst.index(ub.BLOK_EINDE) < tekst.index("## Bekende afwijkingen")
    assert "03-10-2026" in tekst and "0.3.0" in tekst


def test_zonder_bewijs_niet_in_de_galerij(tmp_path):
    map_, root, ucs = _fixture(tmp_path, met_bewijs=False)
    assert "Nog geen bewijs" in ub.galerij_markdown(ucs, map_)
    assert "Nog geen bewijs" in ub.blok_markdown("x", ucs["x"], map_)
    ucs["x"]["status"] = "ontwerp"
    map2, _, _ = _fixture(tmp_path / "b")
    assert "img" not in ub.galerij_markdown(ucs, map2), "alleen actieve use cases in de galerij"


def test_readme_zonder_bewijssectie_krijgt_er_een(tmp_path):
    map_, root, ucs = _fixture(tmp_path)
    p = map_ / "x" / "README.md"
    p.write_text("# X\n\nTekst.\n", encoding="utf-8")
    ub.werk_readme_bij("x", ucs["x"], map_=map_)
    tekst = p.read_text(encoding="utf-8")
    assert tekst.startswith("# X\n\nTekst.\n\n## Bewijs\n\n" + ub.BLOK_START)
    assert tekst.endswith(ub.BLOK_EINDE + "\n")


def test_cli_galerij_controleer():
    assert uc.main(["galerij", "--controleer"]) == 0
