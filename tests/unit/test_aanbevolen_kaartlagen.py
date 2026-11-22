"""Unit tests voor uitlichten van gekoppelde externe kaartlagen (#528)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "templates" / "index.html"
STYLES_CSS = ROOT / "static" / "css" / "styles.css"
APP_JS = ROOT / "static" / "js" / "app.js"
KOMPAS_JS = ROOT / "static" / "js" / "kompas.js"


def test_html_css_en_wiring_voor_aanbevolen_kaartlagen():
    """Container staat boven lagenlijst met aria-live, CSS gebruikt alleen tokens en JS koppelt events."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = STYLES_CSS.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    kompas_js = KOMPAS_JS.read_text(encoding="utf-8")

    # HTML live-region boven externe-lagen-list binnen externe-lagen-sectie
    sec_start = html.index('id="externe-lagen-sectie"')
    sec_end = html.index("</section>", sec_start)
    sec_html = html[sec_start:sec_end]
    assert 'id="externe-lagen-aanbevolen"' in sec_html
    assert 'aria-live="polite"' in sec_html
    assert "hidden" in sec_html
    assert sec_html.index('id="externe-lagen-aanbevolen"') < sec_html.index('id="externe-lagen-list"')
    assert 'href="/static/css/styles.css"' in html
    assert "/static/js/kompas.js?v=3" in html
    assert "/static/js/app.js?v=13" in html

    # CSS blok gebruikt uitsluitend tokens (geen hardcoded hexwaarden)
    css_match = re.search(
        r"/\* Uitgelichte externe kaartlagen bij Kompasthema of indicator \(#528\) \*/.*?(?=\n/\* Slider Styling \*/)",
        css,
        re.DOTALL,
    )
    assert css_match is not None
    css_blok = css_match.group(0)
    css_zonder_comment = re.sub(r"/\*.*?\*/", "", css_blok, flags=re.DOTALL)
    assert ".externe-lagen-aanbevolen[hidden]" in css_blok
    assert ".externe-aanbevolen-header" in css_blok
    assert ".externe-aanbevolen-titel" in css_blok
    assert ".externe-aanbevolen-body" in css_blok
    assert re.search(r"#[0-9a-fA-F]{3,8}", css_zonder_comment) is None

    # Kompas + App EventBus en reset-koppeling
    assert "KOMPAS_THEMA_SELECTED" in kompas_js
    assert "KOMPAS_HIERARCHIE_GELADEN" in kompas_js
    assert kompas_js.count("{ stil: true }") >= 2
    assert "window.EventBus.on('KOMPAS_THEMA_SELECTED'" in app_js
    assert "window.EventBus.on('KOMPAS_HIERARCHIE_GELADEN'" in app_js

    reset_match = re.search(r"function resetKaartIndicator\(\)\s*\{(.*?)\n\}", app_js, re.DOTALL)
    assert reset_match is not None
    reset_body = reset_match.group(1)
    assert "state.actiefKompasThema = null;" in reset_body
    assert "state.actiefKompasPrimaireThemas = [];" in reset_body
    assert "updateAanbevolenExterneLagen();" in reset_body

    aanbevolen_fn = re.search(
        r"function updateAanbevolenExterneLagen\(\)\s*\{(.*?)\n\}\n\nwindow\.updateAanbevolenExterneLagen",
        app_js,
        re.DOTALL,
    )
    assert aanbevolen_fn is not None
    assert "innerHTML" not in aanbevolen_fn.group(1)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js niet gevonden")
def test_node_thema_map_selectie_en_checkbox_sync():
    """Node-evaluatie van bouwKompasIndicatorThemaMap, selecteerAanbevolenExterneLagen en syncExterneLaagCheckboxes."""
    app_js = APP_JS.read_text(encoding="utf-8")

    thema_fn = re.search(
        r"(function bouwKompasIndicatorThemaMap\(hierarchie\).*?window\.bouwKompasIndicatorThemaMap = bouwKompasIndicatorThemaMap;)",
        app_js,
        re.DOTALL,
    )
    sel_fn = re.search(
        r"(function selecteerAanbevolenExterneLagen\(lagen, context = \{\}\).*?window\.selecteerAanbevolenExterneLagen = selecteerAanbevolenExterneLagen;)",
        app_js,
        re.DOTALL,
    )
    sync_fn = re.search(
        r"(function syncExterneLaagCheckboxes\(laagId, checked, disabled = null\).*?window\.syncExterneLaagCheckboxes = syncExterneLaagCheckboxes;)",
        app_js,
        re.DOTALL,
    )
    assert thema_fn is not None and sel_fn is not None and sync_fn is not None

    script = f"""
const window = {{}};
const cbs = [
  {{ id: 'toggle-aanbevolen-laag-7', dataset: {{ laagId: '7' }}, checked: false, disabled: false }},
  {{ id: 'toggle-externe-laag-7', dataset: {{ laagId: '7' }}, checked: false, disabled: false }},
  {{ id: 'toggle-externe-laag-9', dataset: {{ laagId: '9' }}, checked: false, disabled: false }},
];
const sectie = {{
  querySelectorAll: (sel) => sel.includes('data-laag-id') ? cbs : [],
}};
const document = {{
  getElementById: (id) => (id === 'externe-lagen-sectie' ? sectie : null),
  querySelectorAll: () => [],
}};

{thema_fn.group(1)}
{sel_fn.group(1)}
{sync_fn.group(1)}

const boom = {{
  name: 'Root',
  type: 'root',
  children: [
    {{
      name: 'Kwaliteit fysieke leefomgeving',
      type: 'titel',
      children: [
        {{
          name: 'Openbare ruimte',
          type: 'thema',
          children: [
            {{
              name: 'Klimaat',
              type: 'onderdeel',
              children: [
                {{ name: 'Afstand tot koele plek', type: 'indicator', uuid: 'bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c' }},
                {{ name: 'Gevoelstemperatuur', type: 'indicator', uuid: 'fdb4c11b-60ca-4ea1-86b8-6855a83344ee' }},
              ],
            }},
            {{
              name: 'Inrichting',
              type: 'onderdeel',
              children: [
                {{ name: 'Straatmeubilair', type: 'indicator', uuid: '44444444-4444-4444-4444-444444444444' }},
              ],
            }},
          ],
        }},
      ],
    }},
    {{
      name: 'Samenstelling',
      type: 'titel',
      children: [
        {{
          name: 'Bebouwing',
          type: 'thema',
          children: [
            {{
              name: 'Bouwperiode',
              type: 'onderdeel',
              children: [
                {{ name: 'Bouwjaar voor 1915', type: 'indicator', uuid: '3dfcad9b-fad4-47d3-b701-8de88c198d13' }},
              ],
            }},
          ],
        }},
      ],
    }},
  ],
}};

const themaMap = bouwKompasIndicatorThemaMap({{ hierarchie: boom }});

const lagen = [
  {{
    id: 10,
    naam: 'Afstand tot koelte',
    groep_naam: 'Klimaat',
    kompas_thema_naam: 'Klimaat',
    gekoppelde_indicatoren: ['bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c'],
    groep_volgorde: 2,
    volgorde: 1,
  }},
  {{
    id: 8,
    naam: 'Natura 2000 IJsselmeerkust & Wadden',
    groep_naam: 'Natuur',
    kompas_thema_naam: 'Klimaat',
    gekoppelde_indicatoren: [],
    groep_volgorde: 3,
    volgorde: 2,
  }},
  {{
    id: 3,
    naam: 'Rijks Monumenten & Beschermde Stadsgezichten',
    groep_naam: 'Cultuur',
    kompas_thema_naam: 'Bebouwing',
    gekoppelde_indicatoren: ['3dfcad9b-fad4-47d3-b701-8de88c198d13'],
    groep_volgorde: 1,
    volgorde: 1,
  }},
  {{
    id: 99,
    naam: 'Alleen groep Klimaat zonder koppeling',
    groep_naam: 'Klimaat',
    kompas_thema_naam: null,
    gekoppelde_indicatoren: [],
    groep_volgorde: 1,
    volgorde: 1,
  }},
];

const klikKlimaat = selecteerAanbevolenExterneLagen(lagen, {{
  actiefThema: 'Klimaat',
  actiefNodeType: 'onderdeel',
  primaireThemas: ['Klimaat'],
  secundaireThemas: ['Openbare ruimte'],
  themaIndicatorUuids: ['bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c', 'fdb4c11b-60ca-4ea1-86b8-6855a83344ee'],
}});

const klikOpenbareRuimte = selecteerAanbevolenExterneLagen(lagen, {{
  actiefThema: 'Openbare ruimte',
  actiefNodeType: 'thema',
  primaireThemas: ['Openbare ruimte'],
  secundaireThemas: ['Klimaat', 'Inrichting'],
  themaIndicatorUuids: ['bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c', '44444444-4444-4444-4444-444444444444'],
}});

const klikInrichting = selecteerAanbevolenExterneLagen(lagen, {{
  actiefThema: 'Inrichting',
  actiefNodeType: 'onderdeel',
  primaireThemas: ['Inrichting'],
  secundaireThemas: ['Openbare ruimte'],
  themaIndicatorUuids: ['44444444-4444-4444-4444-444444444444'],
}});

const indicatorGevoelstemp = selecteerAanbevolenExterneLagen(lagen, {{
  indicatorUuid: 'fdb4c11b-60ca-4ea1-86b8-6855a83344ee',
  indicatorNaam: 'Gevoelstemperatuur (965 gebieden) · intern',
  indicatorThemas: themaMap['fdb4c11b-60ca-4ea1-86b8-6855a83344ee'],
}});

const klikKwadrantMetActieveIndicator = selecteerAanbevolenExterneLagen(lagen, {{
  actiefThema: 'Kwaliteit fysieke leefomgeving',
  actiefNodeType: 'titel',
  primaireThemas: ['Kwaliteit fysieke leefomgeving'],
  secundaireThemas: [],
  themaIndicatorUuids: [],
  indicatorUuid: 'fdb4c11b-60ca-4ea1-86b8-6855a83344ee',
  indicatorNaam: 'Gevoelstemperatuur (965 gebieden)',
  indicatorThemas: themaMap['fdb4c11b-60ca-4ea1-86b8-6855a83344ee'],
}});

const gewist = selecteerAanbevolenExterneLagen(lagen, {{}});

syncExterneLaagCheckboxes(7, true, true);
const tijdensLaden = cbs.map(c => [c.id, c.checked, c.disabled]);
syncExterneLaagCheckboxes(7, true, false);
const naLaden = cbs.map(c => [c.id, c.checked, c.disabled]);
syncExterneLaagCheckboxes('7', false, false);
const naUit = cbs.map(c => [c.id, c.checked, c.disabled]);

console.log(JSON.stringify({{
  themaMap,
  klikKlimaat: {{ label: klikKlimaat.contextLabel, ids: klikKlimaat.lagen.map(l => l.id) }},
  klikOpenbareRuimte: {{ label: klikOpenbareRuimte.contextLabel, ids: klikOpenbareRuimte.lagen.map(l => l.id) }},
  klikInrichting,
  indicatorGevoelstemp: {{ label: indicatorGevoelstemp.contextLabel, ids: indicatorGevoelstemp.lagen.map(l => l.id) }},
  klikKwadrantMetActieveIndicator: {{
    label: klikKwadrantMetActieveIndicator.contextLabel,
    ids: klikKwadrantMetActieveIndicator.lagen.map(l => l.id),
  }},
  gewist,
  tijdensLaden,
  naLaden,
  naUit,
}}));
"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    res = json.loads(out.stdout)

    assert res["themaMap"] == {
        "bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c": ["Openbare ruimte", "Klimaat", "Kwaliteit fysieke leefomgeving"],
        "fdb4c11b-60ca-4ea1-86b8-6855a83344ee": ["Openbare ruimte", "Klimaat", "Kwaliteit fysieke leefomgeving"],
        "44444444-4444-4444-4444-444444444444": ["Openbare ruimte", "Inrichting", "Kwaliteit fysieke leefomgeving"],
        "3dfcad9b-fad4-47d3-b701-8de88c198d13": ["Bebouwing", "Bouwperiode", "Samenstelling"],
    }
    # Ring-3 Klimaat toont Afstand tot koelte (10) én Natura 2000 (8), niet laaggroep 99 zonder kompas_thema_naam
    assert res["klikKlimaat"] == {"label": "Klimaat", "ids": [10, 8]}
    assert res["klikOpenbareRuimte"] == {"label": "Openbare ruimte", "ids": [10, 8]}
    assert res["klikInrichting"] == {"contextLabel": None, "lagen": []}
    assert res["indicatorGevoelstemp"] == {"label": "Gevoelstemperatuur", "ids": [10, 8]}
    assert res["klikKwadrantMetActieveIndicator"] == {"label": "Gevoelstemperatuur", "ids": [10, 8]}
    assert res["gewist"] == {"contextLabel": None, "lagen": []}
    assert res["tijdensLaden"] == [
        ["toggle-aanbevolen-laag-7", True, True],
        ["toggle-externe-laag-7", True, True],
        ["toggle-externe-laag-9", False, False],
    ]
    assert res["naLaden"] == [
        ["toggle-aanbevolen-laag-7", True, False],
        ["toggle-externe-laag-7", True, False],
        ["toggle-externe-laag-9", False, False],
    ]
    assert res["naUit"] == [
        ["toggle-aanbevolen-laag-7", False, False],
        ["toggle-externe-laag-7", False, False],
        ["toggle-externe-laag-9", False, False],
    ]
