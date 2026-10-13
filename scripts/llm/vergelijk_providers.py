#!/usr/bin/env python3
"""
Vergelijk LLM-aanbieders op vaste scenario's tegen de draaiende app (#88).

Per beschikbare aanbieder: omschakelen met kies_provider.py, daarna elk scenario één keer
(geen herhalingen, vriendelijk voor gratis tiers) en vastleggen: HTTP-status, latency,
modus (LLM of terugval), gekozen acties, woorden, Nederlands-check, grounding-overtredingen
(tests/grounding.py) en een fragment. Aanbieders zonder sleutel: 'overgeslagen (geen key)'.
Aan het eind wordt de oorspronkelijke llm_config teruggezet.

Uitvoer: docs/testcases/llm-vergelijking/<JJJJ-MM-DD>_vergelijking.md en .json

Gebruik (op de host, stack draait met --profile llm-gateway):

    python scripts/llm/vergelijk_providers.py
    python scripts/llm/vergelijk_providers.py --providers ollama,direct-ollama,gemini

Omschakelen gebeurt standaard in de backend-container:
    docker compose exec -T backend python scripts/llm/kies_provider.py ...
Anders opgeven met --kies-cmd of KIES_PROVIDER_CMD (bv. "python scripts/llm/kies_provider.py"
als de host de database en gateway kan bereiken). COMPOSE_PROJECT_NAME/COMPOSE_FILE uit de
omgeving gelden ook voor dat docker-compose-commando.

Alleen standaardbibliotheek (plus tests/grounding.py); geen sleutels in uitvoer of rapport.
"""

import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from tests.grounding import ongegronde_getallen  # noqa: E402

ALLE_PROVIDERS = ["ollama", "direct-ollama", "claude", "openai", "gemini"]
EXTERN = {"claude", "openai", "gemini"}

SCENARIOS = [
    {
        "id": "chat-groen-bolsward",
        "soort": "chat",
        "vraag": "Hoe groen is Bolsward-Zuidoost?",
        "gebied": "BU19000002",
        "label": "Chat: 'Hoe groen is Bolsward-Zuidoost?' (BU19000002)",
    },
    {
        "id": "chat-workum",
        "soort": "chat",
        "vraag": "Wat valt op in Workum?",
        "gebied": "BU19000200",
        "label": "Chat: 'Wat valt op in Workum?' (BU19000200)",
    },
    {
        "id": "rapport-bolsward",
        "soort": "rapport",
        "gebied": "BU19000002",
        "label": "Rapport-narrative BU19000002 (Bolsward-Zuidoost)",
    },
    {
        "id": "rapport-workum",
        "soort": "rapport",
        "gebied": "BU19000200",
        "label": "Rapport-narrative BU19000200 (Workum)",
    },
]

NL_WOORDEN = {
    "de",
    "het",
    "een",
    "en",
    "van",
    "in",
    "is",
    "dat",
    "op",
    "voor",
    "met",
    "niet",
    "zijn",
    "te",
    "er",
    "je",
    "ik",
    "wordt",
    "deze",
    "als",
    "ook",
    "om",
    "bij",
    "naar",
}
FOUTMELDINGEN = ("Error contacting", "LLM-server", "Generatie mislukt", "Fout bij")


# ── HTTP ─────────────────────────────────────────────────────────────────────


def http(methode, url, body=None, timeout=900):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=methode, headers={"Content-Type": "application/json"} if data else {}
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, tekst = r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status, tekst = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # time-out, verbinding
        return None, {"fout": type(e).__name__ + ": " + str(e)[:200]}, round(time.monotonic() - t0, 1)
    duur = round(time.monotonic() - t0, 1)
    try:
        return status, json.loads(tekst), duur
    except ValueError:
        return status, {"fout": tekst[:300]}, duur


# ── kies_provider.py aanroepen ───────────────────────────────────────────────


def kies(cmd, *args):
    """Roept kies_provider.py aan met --json; geeft (exitcode, dict)."""
    r = subprocess.run([*cmd, *args, "--json"], capture_output=True, text=True, encoding="utf-8")
    regels = [x for x in r.stdout.splitlines() if x.strip().startswith("{")]
    try:
        return r.returncode, json.loads(regels[-1]) if regels else {"fout": (r.stderr or r.stdout)[-300:]}
    except ValueError:
        return r.returncode, {"fout": r.stdout[-300:]}


# ── Beoordeling ──────────────────────────────────────────────────────────────


def woorden(tekst):
    return re.findall(r"[\wÀ-ÿ'-]+", (tekst or "").lower())


def is_nederlands(tekst):
    return len({w for w in woorden(tekst) if w in NL_WOORDEN}) >= 3


def fragment(tekst, n=220):
    t = " ".join((tekst or "").split())
    return t if len(t) <= n else t[:n].rstrip() + "…"


def is_fout(tekst):
    return any(f in (tekst or "") for f in FOUTMELDINGEN)


def foutcodes(teksten):
    """HTTP-codes uit foutmeldingen van de backend, bv. '(429)' bij een rate limit."""
    codes = sorted({c for t in teksten if is_fout(t) for c in re.findall(r"\((\d{3})\)", t)})
    return ", ".join(f"HTTP {c}" + (" rate limit" if c == "429" else "") for c in codes) or "geen antwoord"


def run_chat(base, sc, timeout):
    status, data, duur = http(
        "POST", f"{base}/api/chat", {"vraag": sc["vraag"], "context": {"huidig_gebied_id": sc["gebied"]}}, timeout
    )
    res = {"status": status, "latency_s": duur}
    if status != 200:
        res.update(modus="fout", fout=data.get("fout") or data.get("detail"))
        return res
    tekst = data.get("narrative") or ""
    modus = (data.get("debug") or {}).get("mode") or "?"
    bron = {
        "vraag": sc["vraag"],
        "context": {"huidig_gebied_id": sc["gebied"]},
        "indicatoren": [
            {k: i.get(k) for k in ("naam", "beschrijving", "categorie", "eenheid")} for i in data.get("indicatoren", [])
        ],
    }
    res.update(
        modus=modus,
        llm=modus == "intelligent_dispatcher" and not is_fout(tekst),
        model=(data.get("debug") or {}).get("model"),
        acties=[
            f"{a.get('type')}: {a.get('label')}" + (f" [{a.get('indicator_uuid')}]" if a.get("indicator_uuid") else "")
            for a in data.get("acties", [])
        ],
        woorden=len(woorden(tekst)),
        fragment=fragment(tekst),
    )
    if modus.startswith("deterministic"):
        res.update(modus="vast scenario (geen LLM)", nederlands=None, grounding=None)
    elif is_fout(tekst):
        res.update(modus=f"{modus}, LLM-fout ({foutcodes([tekst])})", nederlands=None, grounding=None)
    else:
        res.update(nederlands=is_nederlands(tekst), grounding=ongegronde_getallen(tekst, bron))
    return res


def run_rapport(base, sc, timeout):
    status, data, duur = http("GET", f"{base}/api/report/narrative/{sc['gebied']}", timeout=timeout)
    res = {"status": status, "latency_s": duur}
    if status != 200:
        res.update(modus="fout", fout=data.get("fout") or data.get("detail"))
        return res
    _, payload, _ = http("GET", f"{base}/api/report/data/{sc['gebied']}", timeout=120)
    domeinen = payload.get("significante_domeinen", {}) if isinstance(payload, dict) else {}
    samenvatting = data.get("ai_summary") or ""
    per_domein = data.get("domain_summaries", {})
    teksten = [samenvatting, *per_domein.values()]
    n_fout = sum(is_fout(t) for t in teksten)
    # Grounding en taal alleen over echte modeltekst, niet over foutmeldingen
    grounding = []
    for domein, tekst in per_domein.items():
        if not is_fout(tekst):
            grounding += [
                f"{domein}: {g}"
                for g in ongegronde_getallen(tekst, {"domein": domein, "indicatoren": domeinen.get(domein, [])})
            ]
    if not is_fout(samenvatting):
        grounding += [f"samenvatting: {g}" for g in ongegronde_getallen(samenvatting, payload)]
    if not per_domein:
        modus = "geen domeinen"
    elif n_fout:
        modus = f"LLM-fout in {n_fout}/{len(teksten)} teksten ({foutcodes(teksten)})"
    else:
        modus = "LLM"
    modellen = sorted({d.get("model") for d in data.get("debug_info", []) if isinstance(d, dict) and d.get("model")})
    res.update(
        modus=modus,
        llm=bool(per_domein) and not n_fout,
        model=", ".join(modellen) or None,
        acties=[],
        domeinen=len(per_domein),
        woorden=len(woorden(samenvatting)),
        woorden_totaal=sum(len(woorden(t)) for t in teksten if not is_fout(t)),
        nederlands=None if is_fout(samenvatting) else is_nederlands(samenvatting),
        grounding=None if n_fout == len(teksten) else grounding,
        fragment=fragment(samenvatting),
    )
    return res


# ── Rapport ──────────────────────────────────────────────────────────────────


def cel(r):
    if r.get("overgeslagen"):
        return r["overgeslagen"]
    if r.get("status") != 200:
        return f"❌ HTTP {r.get('status')} ({r.get('latency_s')} s)"
    delen = [f"{r['latency_s']} s", r["modus"]]
    if r.get("nederlands") is not None:
        delen += [f"{r['woorden']} w", "NL ja" if r["nederlands"] else "NL **nee**"]
    if r.get("grounding") is not None:
        g = r["grounding"]
        delen.append("grounding ok" if not g else f"grounding **{len(g)}×**")
    return " · ".join(delen)


def schrijf_rapport(uitdir: Path, meta: dict, resultaten: dict):
    datum = meta["datum"]
    uitdir.mkdir(parents=True, exist_ok=True)
    (uitdir / f"{datum}_vergelijking.json").write_text(
        json.dumps({"meta": meta, "resultaten": resultaten}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    providers = meta["providers"]
    md = [
        f"# LLM-providervergelijking — {datum}",
        "",
        "Gegenereerd door `scripts/llm/vergelijk_providers.py` (#88). Eén run per scenario per aanbieder; "
        "LLM-uitvoer varieert per run, dus dit is een momentopname en geen benchmark.",
        "",
        f"- App: `{meta['base_url']}` · sample dataset",
        "- Aanbieders:",
    ]
    for p in providers:
        b = meta["beschikbaarheid"].get(p, {})
        md.append(
            f"  - `{p}`: {'beschikbaar' if b.get('beschikbaar') else 'overgeslagen'} — {b.get('reden', '')}"
            + (f" · model: `{b['model']}`" if b.get("model") else "")
        )
    md += [
        f"- Oorspronkelijke configuratie teruggezet: {meta.get('hersteld')}",
        "",
        "Legenda: latency · modus (`intelligent_dispatcher` = LLM gaf geldige JSON; `legacy_fallback` = "
        "terugval op regels; `vast scenario` = trefwoord uit `chat_scenarios`, geen LLM; `LLM` = rapporttekst "
        "door het model; `LLM-fout` = de aanbieder gaf een fout, de tekst is een foutmelding) · woorden "
        "(chat: antwoord; rapport: samenvatting) · Nederlands (≥ 3 Nederlandse functiewoorden) · grounding "
        "(getallen die niet in de brondata staan, tests/grounding.py; alleen over echte modeltekst).",
        "",
    ]

    md += [
        "## Overzicht",
        "",
        "| Scenario | " + " | ".join(f"`{p}`" for p in providers) + " |",
        "|---|" + "---|" * len(providers),
    ]
    for sc in SCENARIOS:
        md.append(f"| {sc['label']} | " + " | ".join(cel(resultaten[p][sc["id"]]) for p in providers) + " |")
    md.append("")

    for sc in SCENARIOS:
        md += [f"## {sc['label']}", ""]
        for p in providers:
            r = resultaten[p][sc["id"]]
            if r.get("overgeslagen"):
                md.append(f"- **`{p}`**: {r['overgeslagen']}")
                continue
            if r.get("status") != 200:
                md.append(
                    f"- **`{p}`**: HTTP {r.get('status')} na {r.get('latency_s')} s — {fragment(str(r.get('fout')), 160)}"
                )
                continue
            md.append(
                f"- **`{p}`** ({r['latency_s']} s, {r['modus']}" + (f", {r['model']}" if r.get("model") else "") + ")"
            )
            if sc["soort"] == "chat":
                md.append(f"  - acties: {'; '.join(r['acties']) if r['acties'] else '—'}")
            else:
                md.append(f"  - {r['domeinen']} domeinsamenvattingen, {r['woorden_totaal']} woorden totaal")
            if r["grounding"]:
                md.append(
                    f"  - niet-gegronde getallen: {', '.join(r['grounding'][:10])}"
                    + (" …" if len(r["grounding"]) > 10 else "")
                )
            md.append(f"  - > {r['fragment']}")
        md.append("")
    (uitdir / f"{datum}_vergelijking.md").write_text("\n".join(md), encoding="utf-8")


# ── Hoofdprogramma ───────────────────────────────────────────────────────────


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Vergelijk LLM-aanbieders op vaste scenario's.")
    p.add_argument(
        "--base-url",
        default=os.environ.get("OMNITWIN_BASE_URL", f"http://localhost:{os.environ.get('OMNITWIN_HTTP_PORT', '80')}"),
    )
    p.add_argument(
        "--providers", default=",".join(ALLE_PROVIDERS), help=f"komma-gescheiden, standaard {','.join(ALLE_PROVIDERS)}"
    )
    p.add_argument(
        "--kies-cmd",
        default=os.environ.get(
            "KIES_PROVIDER_CMD", "docker compose exec -T backend python scripts/llm/kies_provider.py"
        ),
    )
    p.add_argument("--uit", default=str(ROOT / "docs" / "testcases" / "llm-vergelijking"))
    p.add_argument("--timeout", type=int, default=900, help="seconden per verzoek")
    # Gratis tiers tellen per minuut (Gemini: 5 verzoeken/min); één rapport-narrative is al
    # 4-6 modelaanroepen. Daarom standaard ruim een minuut tussen scenario's.
    p.add_argument(
        "--pauze-extern",
        type=float,
        default=65.0,
        help="seconden pauze tussen scenario's bij externe aanbieders (rate limits, standaard 65)",
    )
    a = p.parse_args(argv)

    base = a.base_url.rstrip("/")
    cmd = shlex.split(a.kies_cmd)
    providers = [x.strip() for x in a.providers.split(",") if x.strip()]
    onbekend = set(providers) - set(ALLE_PROVIDERS)
    if onbekend:
        p.error(f"onbekende aanbieder(s): {', '.join(sorted(onbekend))}")

    code, origineel = kies(cmd, "status")
    if code != 0 or "api_type" not in origineel:
        print(f"Kan huidige llm_config niet lezen: {origineel}", file=sys.stderr)
        return 1
    _, beschikbaar = kies(cmd, "beschikbaar")
    print(f"Oorspronkelijk actief: {origineel.get('provider')} ({origineel.get('model_name')})")

    meta = {
        "datum": dt.date.today().isoformat(),
        "base_url": base,
        "providers": providers,
        "beschikbaarheid": {k: v for k, v in beschikbaar.items() if k in providers},
        "origineel": {k: origineel.get(k) for k in ("api_type", "api_url", "model_name")},
    }
    resultaten = {}
    try:
        for prov in providers:
            b = beschikbaar.get(prov, {"beschikbaar": False, "reden": "onbekend"})
            if not b.get("beschikbaar"):
                reden = (
                    "overgeslagen (geen key)"
                    if "geen key" in b.get("reden", "")
                    else f"overgeslagen ({b.get('reden')})"
                )
                print(f"{prov}: {reden}")
                resultaten[prov] = {sc["id"]: {"overgeslagen": reden} for sc in SCENARIOS}
                continue
            code, cfg = kies(cmd, prov)
            if code != 0:
                reden = f"overgeslagen ({cfg.get('fout')})"
                print(f"{prov}: {reden}")
                resultaten[prov] = {sc["id"]: {"overgeslagen": reden} for sc in SCENARIOS}
                continue
            print(f"{prov}: actief ({cfg.get('api_type')}, {cfg.get('model_name')})")
            resultaten[prov] = {}
            for i, sc in enumerate(SCENARIOS):
                if i and prov in EXTERN:
                    time.sleep(a.pauze_extern)
                r = (run_chat if sc["soort"] == "chat" else run_rapport)(base, sc, a.timeout)
                resultaten[prov][sc["id"]] = r
                print(f"  {sc['id']:20} {cel(r)}")
    finally:
        o = meta["origineel"]
        code, _ = kies(
            cmd, "herstel", "--api-type", o["api_type"], "--api-url", o["api_url"], "--model", o["model_name"]
        )
        meta["hersteld"] = "ja" if code == 0 else "NEE — controleer llm_config"
        print(f"Oorspronkelijke configuratie teruggezet: {meta['hersteld']}")

    schrijf_rapport(Path(a.uit), meta, resultaten)
    print(f"Rapport: {Path(a.uit) / (meta['datum'] + '_vergelijking.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
