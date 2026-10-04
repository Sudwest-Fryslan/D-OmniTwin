"""
Controleert relatieve links in de Markdown-bestanden van de repository (#204).

Per link in een door git gevolgd `*.md`-bestand:
- het doelbestand of de doelmap bestaat;
- bij een anker naar een Markdown-bestand (`pad.md#kop` of `#kop`) bestaat die kop.

Externe links (http, https, mailto) worden niet gecontroleerd. Links in codeblokken
en inline code tellen niet mee. `docs/archief/` valt erbuiten: die documenten zijn
bevroren en verwijzen naar interne stukken die niet in de repository staan.

Gebruik:
    python tools/check_links.py          # exitcode 1 bij dode links
"""

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
UITGESLOTEN = ("docs/archief/",)

# [tekst](doel) of ![alt](doel "titel"); doel zonder spaties of tussen <...>
INLINE = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
# [label]: doel
REFERENTIE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
HTML_ATTR = re.compile(r"""<(?:a|img)\s[^>]*?(?:href|src)=["']([^"']+)["']""", re.IGNORECASE)
KOP = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
HTML_ANKER = re.compile(r"""<a\s+(?:name|id)=["']([^"']+)["']""", re.IGNORECASE)


def git_md_bestanden() -> list[Path]:
    uit = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [ROOT / p for p in uit.split("\0")
            if p and not p.startswith(UITGESLOTEN) and (ROOT / p).is_file()]


def zonder_code(tekst: str, inline: bool = True) -> str:
    """Codeblokken (en inline code) leegmaken; regels blijven staan voor de regelnummers."""
    regels, in_blok, hek = [], False, ""
    for regel in tekst.splitlines():
        m = re.match(r"^\s*(`{3,}|~{3,})", regel)
        if m and (not in_blok or m.group(1)[0] == hek[0] and len(m.group(1)) >= len(hek)):
            in_blok, hek = (not in_blok), m.group(1)
            regels.append("")
            continue
        if in_blok:
            regels.append("")
        elif inline:
            regels.append(re.sub(r"(`+)(?:(?!\1).)+\1", "", regel))
        else:
            regels.append(regel)
    return "\n".join(regels)


def github_slug(kop: str) -> str:
    """Anker zoals GitHub het maakt: kleine letters, leestekens weg, spaties -> '-'."""
    kop = re.sub(r"<[^>]+>", "", kop)               # HTML-tags
    kop = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", kop)  # links -> tekst
    kop = kop.replace("`", "").lower()
    kop = re.sub(r"[^\w\- ]", "", kop)             # \w houdt letters met accenten en cijfers
    return kop.replace(" ", "-")


def ankers(pad: Path, cache: dict) -> set[str]:
    if pad not in cache:
        gezien: dict[str, int] = {}
        result = set()
        for regel in zonder_code(pad.read_text(encoding="utf-8", errors="ignore"), inline=False).splitlines():
            m = KOP.match(regel)
            if m:
                slug = github_slug(m.group(2))
                n = gezien.get(slug, 0)
                gezien[slug] = n + 1
                result.add(slug if n == 0 else f"{slug}-{n}")
        for regel in pad.read_text(encoding="utf-8", errors="ignore").splitlines():
            result.update(a.lower() for a in HTML_ANKER.findall(regel))
        cache[pad] = result
    return cache[pad]


def dode_links() -> list[str]:
    fouten, cache = [], {}
    for bestand in git_md_bestanden():
        tekst = zonder_code(bestand.read_text(encoding="utf-8", errors="ignore"))
        for nr, regel in enumerate(tekst.splitlines(), start=1):
            doelen = INLINE.findall(regel) + REFERENTIE.findall(regel) + HTML_ATTR.findall(regel)
            for doel in doelen:
                doel = doel.strip("<>")
                if re.match(r"^[a-z][a-z0-9+.-]*:", doel, re.IGNORECASE) or doel.startswith("//"):
                    continue  # extern (http, https, mailto, ...)
                pad_deel, _, anker = doel.partition("#")
                pad_deel = unquote(pad_deel.split("?")[0])
                if pad_deel.startswith("/"):
                    doelpad = ROOT / pad_deel.lstrip("/")
                elif pad_deel:
                    doelpad = (bestand.parent / pad_deel)
                else:
                    doelpad = bestand
                rel = bestand.relative_to(ROOT).as_posix()
                try:
                    doelpad.resolve().relative_to(ROOT)
                except ValueError:
                    # Buiten de repository, bijv. ../../discussions (GitHub-pagina): niet te controleren
                    continue
                if not doelpad.exists():
                    fouten.append(f"{rel}:{nr}: {doel} (bestaat niet)")
                    continue
                if anker and doelpad.is_file() and doelpad.suffix.lower() == ".md":
                    if unquote(anker).lower() not in ankers(doelpad.resolve(), cache):
                        fouten.append(f"{rel}:{nr}: {doel} (anker bestaat niet)")
    return fouten


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fouten = dode_links()
    for f in fouten:
        print(f)
    print(f"{len(fouten)} dode link(s)")
    return 1 if fouten else 0


if __name__ == "__main__":
    sys.exit(main())
