"""
Bewijs per use case (Use Case Specificatie, sectie 12; https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/225)
=====================================================================================================
`python -m omnitwin.usecases bewijs <naam> | --alle` voert de declaratieve stappen uit
`bewijs.stappen` van het manifest uit met Playwright tegen een draaiende installatie
(`OMNITWIN_BASE_URL`), en schrijft in `usecases/<naam>/bewijs/`:

- `<id>.webp` per stap: vaste viewport (1440 × 860), gecomprimeerd tot ≤ 150 KB (in git);
- `bewijs.json`: verslag volgens `docs/specificaties/usecase/1.0/bewijs.schema.json` (in git);
- `volledig/<id>.png`: het origineel, voor de zip bij de release (niet in git).

Daarna worden de README van de use case (blok tussen `<!-- bewijs:start -->` en
`<!-- bewijs:end -->`) en de galerij in de root-README (`<!-- usecase-galerij:start -->`) bijgewerkt.
Alleen bij een release opnieuw maken; dezelfde bestandsnamen worden overschreven.

Acties (vast, geen selectors of scripts in het manifest):

- `open`: pagina `pad` openen;
- `kaart`: viewer met CBS Buurten, gemeentefilter van het gebied, indicator `indicator` (UUID of naam),
  gebied `gebied` geselecteerd en de wijk in beeld (hetzelfde codepad als 'Toon op kaart' in de chat);
- `kompas`: als `kaart`, daarna het Kompas voor het gebied (optioneel `profiel`);
- `chat`: de vraag aan de D-Omni Assistent (zonder taalmodel: de datavraag-route of het scenario);
- `levering`: de status van de laatste levering van `dataset` volgens de laad-API (machineclient);
- `beheer`: beheerpagina `pad` (inloggen met `ADMIN_USER`/`ADMIN_PASSWORD`; testaccounts volgen in #223).

Draaien in de officiële Playwright-image, in het netwerk van de stack:

    docker run --rm --network <project>_default -v "$PWD":/work -w /work \\
        -e OMNITWIN_BASE_URL=http://traefik -e PYTHONPATH=src -e TZ=Europe/Amsterdam \\
        -e OMNITWIN_CLIENT_ID -e OMNITWIN_CLIENT_SECRET \\
        mcr.microsoft.com/playwright/python:v1.63.0-noble \\
        sh -c "pip install -q playwright==1.63.0 pillow requests pyyaml && python -m omnitwin.usecases bewijs --alle"

Controles in het verslag: `api` en `aantal` worden tegen de installatie uitgevoerd; `idempotent`,
`afkeuring` en `bewerking` maken een levering uit de bron en horen bij `test <naam>` (hier
`overgeslagen`); `chat` en `viewer` zijn `overgeslagen` en worden met de screenshots aangetoond.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USECASES_DIR = ROOT / "usecases"
ROOT_README = ROOT / "README.md"
BEWIJS_SCHEMA = ROOT / "docs" / "specificaties" / "usecase" / "1.0" / "bewijs.schema.json"
SPECIFICATIE = "1.0"
VIEWPORT = {"width": 1440, "height": 860}
MAX_BYTES = 150 * 1024
MAX_STAPPEN = 4
BLOK_START, BLOK_EINDE = "<!-- bewijs:start -->", "<!-- bewijs:end -->"
GALERIJ_START, GALERIJ_EINDE = "<!-- usecase-galerij:start -->", "<!-- usecase-galerij:end -->"
# Controles die een levering uit de bron maken: horen bij `test`, niet bij het bewijs
ALLEEN_TEST = ("idempotent", "afkeuring")
TRAAG_MS = int(os.environ.get("BEWIJS_TIMEOUT_MS", "90000"))
# Consolemeldingen van de externe achtergrondkaart zeggen niets over de applicatie (zoals tests/e2e)
CONSOLE_RUIS = (re.compile(r"Failed to load resource", re.I), re.compile(r"tiles?\b|glyphs|sprite", re.I))

_INIT_JS = """
try {
  localStorage.setItem('omnitwin_welcomed', '1');
  for (const k of ['omnitwin_tt_indicator', 'omnitwin_tt_buurt', 'omnitwin_tt_kompas', 'omnitwin_tt_ai']) {
    localStorage.setItem(k, '1');
  }
  localStorage.setItem('omnitwin-gemeente', %s);
  localStorage.setItem('omnitwin-theme', 'light');  // bewijs in de dagstand
} catch (e) {}
"""


# ------------------------------------------------------------------ manifest en bestanden


def stappen(uc: dict) -> list:
    return (uc.get("bewijs") or {}).get("stappen") or []


def bewijsmap(naam: str, map_: Path = USECASES_DIR) -> Path:
    return Path(map_) / naam / "bewijs"


def lees_verslag(naam: str, map_: Path = USECASES_DIR) -> dict | None:
    pad = bewijsmap(naam, map_) / "bewijs.json"
    return json.loads(pad.read_text(encoding="utf-8")) if pad.exists() else None


def gemeentecode(gebied: str | None) -> str:
    """Code van het gemeentefilter (zonder GM) uit een CBS-gebiedscode: BU19000002, WK190000, GM1900 → 1900."""
    m = re.match(r"^(?:BU|WK|GM)(\d{4})", gebied or "")
    return m.group(1) if m else ""


def comprimeer(png: bytes, doel: Path, max_bytes: int = MAX_BYTES) -> int:
    """PNG → WebP ≤ max_bytes: eerst de kwaliteit omlaag, pas daarna kleiner schalen. Geeft de grootte."""
    from PIL import Image

    beeld = Image.open(io.BytesIO(png)).convert("RGB")
    schaal = 1.0
    while True:
        b = (
            beeld
            if schaal == 1.0
            else beeld.resize((round(beeld.width * schaal), round(beeld.height * schaal)), Image.LANCZOS)
        )
        for kwaliteit in (82, 74, 66, 58, 50, 42):
            buf = io.BytesIO()
            b.save(buf, "WEBP", quality=kwaliteit, method=6)
            if buf.tell() <= max_bytes:
                doel.write_bytes(buf.getvalue())
                return buf.tell()
        schaal *= 0.85
        if schaal < 0.3:
            raise ValueError(f"{doel.name}: niet onder {max_bytes} bytes te krijgen")


def _zonder_host(tekst: str, basis: str, lengte: int = 300) -> str:
    """Geen hostnamen in het verslag (specificatie 12.2); ingekort."""
    return tekst.replace(basis, "")[:lengte]


# ------------------------------------------------------------------ uitvoerder (Playwright)


class Stapfout(Exception):
    """Een stap kon niet worden uitgevoerd (pagina laadde niet, gebied of indicator onbekend, ...)."""


class Bewijsmaker:
    """Voert de bewijsstappen van een use case uit in één browser."""

    def __init__(self, browser, basis: str, tok=None):
        """tok: een token, of een functie die een nieuw token geeft (tokens van de machineclient verlopen
        na enkele minuten; een run met --alle duurt langer)."""
        self.browser, self.basis, self._tok_bron = browser, basis.rstrip("/"), tok
        self._tok, self._tok_tijd = None, 0.0
        self.ai_aanbieder = None

    @property
    def tok(self) -> str | None:
        if not callable(self._tok_bron):
            return self._tok_bron
        if self._tok is None or time.time() - self._tok_tijd > 60:
            self._tok, self._tok_tijd = self._tok_bron(), time.time()
        return self._tok

    # -- pagina's

    def _context(self, gemeente: str = ""):
        ctx = self.browser.new_context(viewport=VIEWPORT, locale="nl-NL", color_scheme="light", reduced_motion="reduce")
        ctx.add_init_script(_INIT_JS % json.dumps(gemeente))
        return ctx

    def _start_app(self, page):
        page.goto(f"{self.basis}/", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => window.state && window.state.deckgl && window.kompasViz && window.chatPanel"
            " && document.querySelectorAll('#gebiedstype-select option').length > 1",
            timeout=TRAAG_MS,
        )
        page.add_style_tag(content="#contextual-tooltip { display: none !important; }")

    def _wacht_op_rust(self, page, ms: int = 2500):
        """Netwerk stil en de achtergrondkaart getekend."""
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        page.wait_for_timeout(ms)

    def _buurtenkaart(self, page, gebied: str | None, indicator: str | None, camera: bool = True):
        """CBS Buurten, indicator op de kaart, gebied geselecteerd, de wijk van het gebied in beeld."""
        gebiedstype = page.evaluate(
            "() => { const o = [...document.querySelectorAll('#gebiedstype-select option')]"
            ".find(o => /CBS Buurten/i.test(o.textContent)); return o ? o.value : null; }"
        )
        if not gebiedstype:
            raise Stapfout("gebiedstype CBS Buurten niet gevonden")
        page.evaluate("(id) => window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {ids: [], gebiedstypeId: id})", gebiedstype)
        page.wait_for_function(
            "() => document.querySelectorAll('#indicator-select option').length > 1", timeout=TRAAG_MS
        )
        uuid, naam = None, ""
        if indicator:
            gevonden = page.evaluate(
                """(w) => { const opts = [...document.querySelectorAll('#indicator-select option')].filter(o => o.value);
                    const o = opts.find(o => o.value === w) || opts.find(o => o.textContent.trim() === w)
                          || opts.find(o => o.textContent.toLowerCase().includes(w.toLowerCase()));
                    return o ? [o.value, o.textContent.trim()] : null; }""",
                indicator,
            )
            if not gevonden:
                raise Stapfout(f"indicator {indicator!r} niet gevonden bij CBS Buurten")
            uuid, naam = gevonden
        ids = [gebied] if gebied and gebied.startswith("BU") else []
        # Zonder zoom: de camera zet _toon_omgeving (de wijk in beeld, niet alleen de buurt)
        page.evaluate(
            "([ids, uuid, naam]) => window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {ids, uuid, name: naam, zoom: false})",
            [ids, uuid, naam],
        )
        page.wait_for_function(
            "([uuid, n]) => window.state.currentData && window.state.deckgl.props.layers.some("
            "l => l && l.id && l.id.startsWith('gebieden-layer-')) && (!uuid || window.state.currentIndicator === uuid)"
            " && window.state.selectedGebiedIds.size === n",
            arg=[uuid, len(ids)],
            timeout=TRAAG_MS,
        )
        self._wacht_op_rust(page, 1000)
        if gebied and camera:
            self._toon_omgeving(page, gebied)

    def _toon_omgeving(self, page, gebied: str):
        """Camera op de wijk van een buurt (BU19000002 → alle BU190000..), of op het gebied zelf."""
        prefix = gebied[:8] if gebied.startswith("BU") else gebied
        ok = page.evaluate(
            """(prefix) => {
                const s = window.state, ids = s.currentData.features.map(f => f.properties.id || f.id);
                const kies = ids.filter(i => i && (prefix.startsWith('BU') ? i.startsWith(prefix) : true));
                if (!kies.length) return false;
                const set = new Set(kies); let x0 = 180, x1 = -180, y0 = 90, y1 = -90;
                const walk = a => { if (typeof a[0] === 'number') { x0 = Math.min(x0, a[0]); x1 = Math.max(x1, a[0]);
                    y0 = Math.min(y0, a[1]); y1 = Math.max(y1, a[1]); } else a.forEach(walk); };
                s.currentData.features.filter(f => set.has(f.properties.id || f.id)).forEach(f => walk(f.geometry.coordinates));
                const el = document.getElementById('map');
                const links = document.querySelector('.panel-container.open') ? 360 : 0;
                let rechts = document.getElementById('chat-panel')?.classList.contains('open') ? 380 : 0;
                const kw = document.getElementById('kompas-window');
                if (kw && kw.style.display !== 'none' && kw.getBoundingClientRect().width)
                    rechts = Math.max(rechts, el.clientWidth - kw.getBoundingClientRect().left);
                const vp = new deck.WebMercatorViewport({width: el.clientWidth, height: el.clientHeight}).fitBounds(
                    [[x0, y0], [x1, y1]], {padding: {top: 80, bottom: 120, left: 110 + links, right: 60 + rechts}, maxZoom: 15});
                s.currentViewState = {...s.currentViewState, longitude: vp.longitude, latitude: vp.latitude,
                                      zoom: vp.zoom, pitch: 0, bearing: 0, transitionDuration: 0};
                s.deckgl.setProps({viewState: s.currentViewState});
                return true;
            }""",
            prefix,
        )
        if not ok:
            raise Stapfout(f"gebied {gebied} niet op de kaart")
        self._wacht_op_rust(page, 4000)  # tegels van de achtergrondkaart (PDOK)

    def _kompas(self, page, gebied: str | None, profiel: str | None):
        if profiel:
            gevonden = page.evaluate(
                """async (naam) => { const r = await fetch('/api/kompas/configuraties'); const d = await r.json();
                    const c = (d.configuraties || []).find(c => c.naam === naam || (c.naam || '').includes(naam));
                    if (!c) return false; window.kompasViz.currentConfigId = c.id;
                    const sel = document.getElementById('kompas-config-select'); if (sel) sel.value = c.id; return true; }""",
                profiel,
            )
            if not gevonden:
                raise Stapfout(f"Kompas-profiel {profiel!r} niet gevonden")
        page.evaluate("() => window.openKompasVenster()")
        if gebied and gebied.startswith("BU"):
            page.wait_for_function(
                "(id) => window.kompasViz.currentGebiedId === id"
                " && /Indicatordekking/.test(document.getElementById('kompas-info')?.textContent || '')",
                arg=gebied,
                timeout=TRAAG_MS,
            )
        page.wait_for_function(
            "() => document.querySelectorAll('#kompas-container path.kompas-arc-path').length > 10", timeout=TRAAG_MS
        )
        # Venster naar de rechterrand (zoals tests/e2e), de kaart met het gebied links ervan
        kop = page.locator("#kompas-window .floating-window-header h3").bounding_box()
        if kop:
            x, y = kop["x"] + 20, kop["y"] + kop["height"] / 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 2000, y, steps=10)
            page.mouse.up()
        if gebied:
            self._toon_omgeving(page, gebied)
        self._wacht_op_rust(page, 2500)

    def _chat(self, page, vraag: str) -> str:
        page.locator("#chat-toggle-btn").click()
        invoer = page.locator("#chat-input")
        invoer.fill(vraag)
        with page.expect_response(
            lambda r: r.url.endswith("/api/chat") and r.request.method == "POST",
            timeout=int(os.environ.get("BEWIJS_CHAT_TIMEOUT_MS", "300000")),
        ) as resp:
            invoer.press("Enter")
        data = resp.value.json()
        debug = data.get("debug") or {}
        self.ai_aanbieder = (
            (debug.get("model") or debug.get("provider") or "onbekend")
            if debug.get("llm_gebruikt")
            else (self.ai_aanbieder or "geen")
        )
        page.locator(".chat-message-assistant").last.wait_for(timeout=TRAAG_MS)
        if data.get("kaart_actie"):  # de kaart beweegt mee; laag en tegels laten landen
            page.wait_for_timeout(1500)
        # De vraag bovenaan in beeld, met zoveel mogelijk van het antwoord eronder
        page.evaluate(
            "() => { const v = [...document.querySelectorAll('.chat-message-user')].pop();"
            " if (v) v.scrollIntoView({block: 'start'}); }"
        )
        self._wacht_op_rust(page, 3000)
        return (data.get("narrative") or page.locator(".chat-message-assistant").last.inner_text()).strip()

    def leveringsstatus(self, dataset: str) -> dict:
        """Dataset en laatste levering volgens de laad-API (machineclient nodig)."""
        import requests

        if not self.tok:
            raise Stapfout(
                "geen machineclient (OMNITWIN_CLIENT_ID/OMNITWIN_CLIENT_SECRET): leveringsstatus niet op te vragen"
            )
        h = {"Authorization": f"Bearer {self.tok}"}
        r = requests.get(f"{self.basis}/api/laden/v1/datasets/{dataset}", headers=h, timeout=30)
        if r.status_code == 404:
            raise Stapfout(f"dataset {dataset} is niet geregistreerd")
        r.raise_for_status()  # 401/403: token of rechten; geen reden om de use case over te slaan
        ds = r.json()
        lv = {}
        laatste = (ds.get("laatsteLevering") or {}).get("id")
        if laatste:
            r = requests.get(f"{self.basis}/api/laden/v1/leveringen/{laatste}", headers=h, timeout=30)
            lv = r.json() if r.status_code == 200 else {}
        return {"dataset": ds, "levering": lv}

    def _levering(self, page, dataset: str, uc: dict):
        st = self.leveringsstatus(dataset)
        page.set_content(_leveringspagina(dataset, uc, st["dataset"], st["levering"]), wait_until="load")
        page.wait_for_timeout(300)
        return st

    def _beheer(self, page, pad: str):
        wachtwoord = os.environ.get("ADMIN_PASSWORD")
        if not wachtwoord:
            raise Stapfout("geen beheeraccount (ADMIN_PASSWORD); testaccounts volgen in #223")
        page.goto(f"{self.basis}/admin/login")
        page.get_by_label("Gebruikersnaam").fill(os.environ.get("ADMIN_USER", "admin"))
        page.get_by_label("Wachtwoord").fill(wachtwoord)
        page.get_by_role("button", name="Aanmelden").click()
        page.wait_for_url("**/admin/dashboard", timeout=TRAAG_MS)
        page.goto(f"{self.basis}/admin{pad}" if not pad.startswith("/admin") else f"{self.basis}{pad}")
        self._wacht_op_rust(page, 2500)

    # -- één stap

    def stap(self, uc: dict, s: dict, uit: Path, volledig: Path | None) -> dict:
        ctx = self._context(gemeentecode(s.get("gebied")))
        page = ctx.new_page()
        page.set_default_timeout(TRAAG_MS)
        fouten = []
        page.on("pageerror", lambda e: fouten.append(f"pageerror: {e}"))
        page.on(
            "console",
            lambda m: (
                fouten.append(m.text) if m.type == "error" and not any(p.search(m.text) for p in CONSOLE_RUIS) else None
            ),
        )
        res = {"id": s["id"], "resultaat": "ok", "afbeelding": f"{s['id']}.webp"}
        melding = None
        begin = time.time()
        try:
            actie = s["actie"]
            if actie == "open":
                page.goto(f"{self.basis}{s['pad']}", wait_until="load")
                self._wacht_op_rust(page, 1500)
            elif actie in ("kaart", "kompas"):
                self._start_app(page)
                self._buurtenkaart(page, s.get("gebied"), s.get("indicator"), camera=actie == "kaart")
                if actie == "kompas":
                    self._kompas(page, s.get("gebied"), s.get("profiel"))
            elif actie == "chat":
                self._start_app(page)
                res["antwoord"] = self._chat(page, s["vraag"])
            elif actie == "levering":
                self._levering(page, s["dataset"], uc)
            elif actie == "beheer":
                self._beheer(page, s["pad"])
            else:
                raise Stapfout(f"onbekende actie {actie}")
            res["antwoordtijd_s"] = round(time.time() - begin, 1)
            tekst = page.locator("body").inner_text()
            ontbreekt = [t for t in s.get("bevat", []) if t not in tekst]
            if ontbreekt:
                melding = f"niet zichtbaar: {', '.join(ontbreekt)}"
        except Exception as e:  # de stap mislukt, het scherm bewaren we wel
            melding = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
        if melding:
            res["resultaat"] = "fout"
            fouten.insert(0, f"stap: {melding}")
        try:
            png = page.screenshot(type="png")
            if volledig:
                volledig.mkdir(parents=True, exist_ok=True)
                (volledig / f"{s['id']}.png").write_bytes(png)
            res["_bytes"] = comprimeer(png, uit / res["afbeelding"])
        except Exception as e:
            res["resultaat"] = "fout"
            fouten.append(f"screenshot: {type(e).__name__}: {e}")
        res["console_fouten"] = [_zonder_host(f, self.basis) for f in fouten[:10]]
        if "antwoord" in res:
            res["antwoord"] = (
                _zonder_host(res["antwoord"], self.basis) if len(res["antwoord"]) <= 300 else res["antwoord"][:1500]
            )
        ctx.close()
        return res


def _esc(t) -> str:
    import html

    return html.escape(str(t if t is not None else "–"))


def _leveringspagina(dataset: str, uc: dict, ds: dict, lv: dict) -> str:
    aantallen = lv.get("aantallen") or {}
    rijen = [
        ("Dataset", dataset),
        ("Profiel", ds.get("profiel")),
        ("Huidige versie", ds.get("huidigeVersie", ds.get("versie"))),
        ("Laatste levering", lv.get("id")),
        ("Status", lv.get("status")),
        ("Versie na levering", lv.get("versie")),
        ("Ontvangen", lv.get("ontvangen") or lv.get("aangemaakt")),
        ("Gepubliceerd", lv.get("gepubliceerd")),
    ]
    rijen += [(f"Aantal {k}", f"{v:,}".replace(",", ".") if isinstance(v, int) else v) for k, v in aantallen.items()]
    titel = (ds.get("beschrijving") or {}).get("dct:title") or dataset
    fouten = lv.get("fouten") or []
    tabel = "".join(f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in rijen if v not in (None, ""))
    status = lv.get("status") or "geen levering"
    kleur = "#1b7a3d" if status == "gepubliceerd" else "#a15c00"
    return f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Leveringsstatus {_esc(dataset)}</title>
<style>body{{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:#f4f6f8;color:#1d2733;margin:0;padding:48px 64px}}
h1{{font-size:26px;margin:0 0 4px}} .sub{{color:#5b6b7b;margin:0 0 24px}} .kaart{{background:#fff;border-radius:12px;
box-shadow:0 1px 4px rgba(0,0,0,.12);padding:24px 32px;max-width:980px}} .status{{display:inline-block;padding:4px 14px;
border-radius:14px;color:#fff;background:{kleur};font-weight:600;margin-bottom:16px}} table{{border-collapse:collapse;width:100%}}
th{{text-align:left;color:#5b6b7b;font-weight:500;width:240px}} th,td{{padding:8px 0;border-bottom:1px solid #e6eaee;font-size:16px}}
.voet{{color:#5b6b7b;font-size:13px;margin-top:18px}}</style></head><body>
<h1>Leveringsstatus: {_esc(titel)}</h1>
<p class="sub">Use case <b>{_esc(uc.get("naam"))}</b> {_esc(uc.get("versie"))} · laad-API <code>GET /api/laden/v1/datasets/{_esc(dataset)}</code> en <code>/leveringen/&lt;id&gt;</code></p>
<div class="kaart"><span class="status">{_esc(status)}</span><table>{tabel}</table>
{"<p>Fouten: " + _esc(len(fouten)) + "</p>" if fouten else ""}
<p class="voet">Weergave van de JSON van de laad-API door de use-case-uitvoerder (python -m omnitwin.usecases bewijs).</p></div>
</body></html>"""


# ------------------------------------------------------------------ verslag


def controles(uc: dict, basis: str, tok: str | None) -> list:
    """Controles uit het manifest tegen de installatie: api en aantal; de rest overgeslagen (zie module)."""
    import requests
    from omnitwin import usecases as u

    api = None
    if tok:
        api = u.LaadApi(basis, tok)
    uit = []
    for c in uc.get("controles", []):
        r = {"type": c["type"]}
        if c.get("omschrijving"):
            r["omschrijving"] = c["omschrijving"]
        if c["type"] in ALLEEN_TEST:
            r.update(
                resultaat="overgeslagen",
                melding=f"maakt een levering uit de bron: python -m omnitwin.usecases test {uc['naam']}",
            )
        elif c["type"] in ("chat", "viewer"):
            r.update(
                resultaat="overgeslagen", melding=f"{c['type']}-controles nog niet in de uitvoerder; zie de screenshots"
            )
        elif c["type"] == "aantal" and api is None:
            r.update(resultaat="overgeslagen", melding="geen machineclient (OMNITWIN_CLIENT_ID/OMNITWIN_CLIENT_SECRET)")
        elif c["type"] == "api" and not c.get("anoniem") and api is None:
            r.update(resultaat="overgeslagen", melding="geen machineclient (OMNITWIN_CLIENT_ID/OMNITWIN_CLIENT_SECRET)")
        else:
            anon = api or type("Anoniem", (), {"basis": basis, "s": requests.Session()})()
            try:
                melding = u.controle_api(c, anon, uc)
            except Exception as e:
                melding = f"{type(e).__name__}: {e}"
            if melding is None:
                r["resultaat"] = "ok"
            else:
                r.update(
                    resultaat="overgeslagen" if str(melding).startswith("overgeslagen") else "fout",
                    melding=_zonder_host(str(melding), basis),
                )
        uit.append(r)
    return uit


def omnitwin_versie(basis: str) -> str:
    import requests

    try:
        v = requests.get(f"{basis}/health", timeout=15).json().get("version")
        if v:
            return str(v)
    except Exception:
        pass
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def schemafouten(verslag: dict) -> list:
    from omnitwin.laden.registratie import valideer

    schema = json.loads(BEWIJS_SCHEMA.read_text(encoding="utf-8"))
    return valideer(verslag, schema, schema)


def maak(namen: list, ucs: dict, basis: str, tok: str | None = None, volledig: bool = True) -> dict:
    """Bewijs voor de use cases maken. Geeft per naam het verslag (of de reden waarom niet)."""
    from playwright.sync_api import sync_playwright

    resultaat = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
        )
        for naam in namen:
            uc = ucs[naam]
            if not stappen(uc):
                print(f"⏭️  {naam}: geen bewijs.stappen in het manifest")
                resultaat[naam] = "geen stappen"
                continue
            maker = Bewijsmaker(browser, basis, tok)
            resultaat[naam] = maak_een(maker, uc, volledig)
        browser.close()
    return resultaat


def niet_geleverd(maker: Bewijsmaker, uc: dict) -> list:
    """Datasets van de use case zonder gepubliceerde levering (bron hier niet beschikbaar), als dat te zien is."""
    if not maker.tok:
        return []
    uit = []
    for ds in uc.get("datasets", []):
        try:
            if not maker.leveringsstatus(ds["id"])["dataset"].get("laatsteLevering"):
                uit.append(ds["id"])
        except Stapfout:  # niet geregistreerd
            uit.append(ds["id"])
    return uit


def maak_een(maker: Bewijsmaker, uc: dict, volledig: bool = True):
    naam = uc["naam"]
    ontbreekt = niet_geleverd(maker, uc)
    if ontbreekt:
        print(
            f"⏭️  {naam}: overgeslagen, geen levering voor {', '.join(ontbreekt)} (bron hier niet beschikbaar?); "
            "bestaand bewijs blijft staan"
        )
        return f"overgeslagen: geen levering voor {', '.join(ontbreekt)}"
    uit = bewijsmap(naam)
    uit.mkdir(parents=True, exist_ok=True)
    ids = {s["id"] for s in stappen(uc)}
    for oud in uit.glob("*.webp"):  # stappen die uit het manifest verdwenen
        if oud.stem not in ids:
            oud.unlink()
    res_stappen = []
    for s in stappen(uc)[:MAX_STAPPEN]:
        r = maker.stap(uc, s, uit, uit / "volledig" if volledig else None)
        grootte = r.pop("_bytes", 0)
        teken = "✅" if r["resultaat"] == "ok" else "❌"
        print(
            f"{teken} {naam}/{r['afbeelding']}: {grootte / 1024:.0f} KB, {r.get('antwoordtijd_s', '–')} s"
            + (f"; {r['console_fouten'][0]}" if r["resultaat"] != "ok" else ""),
            flush=True,
        )
        res_stappen.append(r)
    ctr = controles(uc, maker.basis, maker.tok)
    for c in ctr:
        teken = {"ok": "✅", "overgeslagen": "⏭️ ", "fout": "❌"}[c["resultaat"]]
        print(f"   {teken} controle {c['type']}: {c.get('omschrijving', '')} {c.get('melding', '')}".rstrip())
    verslag = {
        "specificatie": SPECIFICATIE,
        "naam": naam,
        "versie": uc["versie"],
        "omnitwin_versie": omnitwin_versie(maker.basis),
        "datum": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if maker.ai_aanbieder:
        verslag["ai_aanbieder"] = maker.ai_aanbieder
    verslag["geslaagd"] = all(c["resultaat"] != "fout" for c in ctr) and all(
        s["resultaat"] == "ok" for s in res_stappen
    )
    verslag["controles"] = ctr
    verslag["stappen"] = res_stappen
    leveringen = []
    if maker.tok:
        for ds in uc.get("datasets", []):
            try:
                lv = maker.leveringsstatus(ds["id"])["levering"]
            except Stapfout:
                continue
            if lv:
                item = {"dataset": ds["id"], "status": lv.get("status", "onbekend")}
                if isinstance(lv.get("versie"), int):
                    item["datasetversie"] = lv["versie"]
                if lv.get("aantallen"):
                    item["aantallen"] = lv["aantallen"]
                leveringen.append(item)
    if leveringen:
        verslag["leveringen"] = leveringen
    fouten = schemafouten(verslag)
    if fouten:
        raise ValueError(f"{naam}: bewijs.json voldoet niet aan het schema: {fouten[:3]}")
    (uit / "bewijs.json").write_text(
        json.dumps(verslag, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{'✅' if verslag['geslaagd'] else '❌'} {naam}: bewijs.json ({len(res_stappen)} stappen)")
    return verslag


def zip_volledig(doel: Path, namen: list | None = None) -> Path:
    """Volledig bewijs (originelen, verslagen) als zip voor de GitHub-release."""
    doel = Path(doel)
    doel.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(doel, "w", zipfile.ZIP_DEFLATED) as z:
        for map_ in sorted(USECASES_DIR.glob("*/bewijs")):
            if namen and map_.parent.name not in namen:
                continue
            for p in sorted(map_.rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(USECASES_DIR).as_posix())
    return doel


# ------------------------------------------------------------------ README-blok en galerij


def _datum_nl(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d-%m-%Y")
    except ValueError:
        return iso[:10]


def blok_markdown(naam: str, uc: dict, map_: Path = USECASES_DIR) -> str:
    """Screenshots in de README van de use case (tussen BLOK_START en BLOK_EINDE)."""
    verslag = lees_verslag(naam, map_)
    if not verslag:
        return f"*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs {naam}`.*"
    regels = [
        f"*Gemaakt op {_datum_nl(verslag['datum'])} met D-OmniTwin {verslag['omnitwin_versie']} "
        f"(use case {verslag['versie']}); {'geslaagd' if verslag['geslaagd'] else '**niet geslaagd**'}. "
        f"Verslag: [`bewijs/bewijs.json`](bewijs/bewijs.json). Opnieuw maken (bij een release): "
        f"`python -m omnitwin.usecases bewijs {naam}`.*"
    ]
    per_id = {s["id"]: s for s in verslag.get("stappen", [])}
    for s in stappen(uc):
        if s["id"] not in per_id or not (bewijsmap(naam, map_) / f"{s['id']}.webp").exists():
            continue
        tekst = s.get("omschrijving") or s["id"]
        regels += ["", f"![{tekst}](bewijs/{s['id']}.webp)", f"*{tekst}*"]
    return "\n".join(regels)


def galerij_markdown(ucs: dict, map_: Path = USECASES_DIR) -> str:
    """Galerij voor de root-README: per actieve use case met bewijs een thumbnail, titel, vraag en link."""
    regels = ["| | Use case |", "|---|---|"]
    for naam, uc in sorted(ucs.items()):
        if uc.get("status") != "actief" or not stappen(uc) or not lees_verslag(naam, map_):
            continue
        eerste = next((s for s in stappen(uc) if (bewijsmap(naam, map_) / f"{s['id']}.webp").exists()), None)
        if not eerste:
            continue
        alt = (eerste.get("omschrijving") or uc.get("titel", naam)).replace('"', "'")
        vraag = " ".join(str(uc.get("vraag", "")).split()).replace("|", "\\|")
        regels.append(
            f'| <a href="usecases/{naam}/README.md"><img src="usecases/{naam}/bewijs/{eerste["id"]}.webp" '
            f'width="320" alt="{alt}"></a> | **[{uc.get("titel", naam)}](usecases/{naam}/README.md)**<br>{vraag} |'
        )
    if len(regels) == 2:
        return "*Nog geen bewijs: `python -m omnitwin.usecases bewijs --alle` tegen een draaiende installatie.*"
    return "\n".join(regels)


def _vervang(tekst: str, start: str, einde: str, inhoud: str) -> str:
    voor, rest = tekst.split(start, 1)
    _, na = rest.split(einde, 1)
    return f"{voor}{start}\n{inhoud}\n{einde}{na}"


def _schrijf_als_anders(pad: Path, nieuw: str, oud: str, crlf: bool, controleer: bool) -> bool:
    if nieuw == oud:
        return True
    if controleer:
        return False
    pad.write_bytes((nieuw.replace("\n", "\r\n") if crlf else nieuw).encode("utf-8"))
    return True


def _lees(pad: Path):
    ruw = Path(pad).read_bytes().decode("utf-8")
    return ruw.replace("\r\n", "\n"), "\r\n" in ruw


def werk_readme_bij(naam: str, uc: dict, controleer: bool = False, map_: Path = USECASES_DIR) -> bool:
    """Blok met screenshots in usecases/<naam>/README.md. Zonder markers: na de kop '## Bewijs' (de oude
    tekst daaronder vervalt) of als nieuwe sectie vóór '## Bekende afwijkingen' of aan het eind."""
    pad = Path(map_) / naam / "README.md"
    tekst, crlf = _lees(pad)
    blok = blok_markdown(naam, uc, map_)
    if BLOK_START in tekst and BLOK_EINDE in tekst:
        nieuw = _vervang(tekst, BLOK_START, BLOK_EINDE, blok)
    else:
        sectie = f"## Bewijs\n\n{BLOK_START}\n{blok}\n{BLOK_EINDE}\n"
        m = re.search(r"^## Bewijs[^\n]*\n.*?(?=^## |\Z)", tekst, re.M | re.S)
        if m:
            nieuw = tekst[: m.start()] + sectie + ("\n" if m.end() < len(tekst) else "") + tekst[m.end() :]
        else:
            m = re.search(r"^## Bekende afwijkingen", tekst, re.M)
            nieuw = (
                (tekst[: m.start()] + sectie + "\n" + tekst[m.start() :]) if m else tekst.rstrip("\n") + "\n\n" + sectie
            )
    return _schrijf_als_anders(pad, nieuw, tekst, crlf, controleer)


def werk_galerij_bij(
    ucs: dict, controleer: bool = False, readme: Path = ROOT_README, map_: Path = USECASES_DIR
) -> bool:
    """Galerij in de root-README en de blokken in de README's van de use cases met bewijs.stappen.
    True = alles actueel (of bijgewerkt)."""
    tekst, crlf = _lees(readme)
    if GALERIJ_START not in tekst or GALERIJ_EINDE not in tekst:
        raise ValueError(f"markers {GALERIJ_START} / {GALERIJ_EINDE} ontbreken in {readme}")
    actueel = _schrijf_als_anders(
        Path(readme),
        _vervang(tekst, GALERIJ_START, GALERIJ_EINDE, galerij_markdown(ucs, map_)),
        tekst,
        crlf,
        controleer,
    )
    for naam, uc in sorted(ucs.items()):
        if stappen(uc) and (Path(map_) / naam / "README.md").exists():
            actueel = werk_readme_bij(naam, uc, controleer, map_) and actueel
    return actueel
