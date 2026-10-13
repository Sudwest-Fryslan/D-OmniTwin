"""
Meet hoe goed de D-Omni Assistent de juiste indicatoren vindt (#233).

    python scripts/ai/evalueer_assistent.py --url http://localhost:8105
    python scripts/ai/evalueer_assistent.py --url http://localhost:8105 --json uitslag.json

Vragen en verwachte indicatoren: tests/data/assistent_evaluatie.json.
Maten en uitleg: src/omnitwin/assistent_evaluatie.py.
Exitcode 1 als een maat onder de drempel uit het testbestand ligt (afgestemd: 'drempels',
holdout: 'drempels_holdout').
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from omnitwin.assistent_evaluatie import (  # noqa: E402
    TESTSET,
    drempelfouten,
    evalueer,
    http_zoek_en_chat,
    laad_testset,
    precision_at_k,
    reciprocal_rank,
    scoor,
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--url", default="http://localhost", help="basis-URL van de installatie")
    p.add_argument("--testset", default=str(TESTSET))
    p.add_argument("--json", help="schrijf de resultaten per vraag naar dit bestand")
    p.add_argument("-v", "--verbose", action="store_true", help="toon elke vraag")
    a = p.parse_args()

    testset = laad_testset(Path(a.testset))
    k = testset.get("k", 3)
    zoek, chat = http_zoek_en_chat(a.url)
    resultaten = evalueer(testset, zoek, chat)
    for r in resultaten:
        p_k = precision_at_k(r["gevonden"], r["relevant"], k)
        rr = reciprocal_rank(r["gevonden"], r["relevant"])
        if a.verbose or rr == 0 or p_k < 0.5 or r["gerouteerd"] is False:
            route = (
                ""
                if r["gerouteerd"] is None
                else (" route=ok" if r["gerouteerd"] else f" route=FOUT ({r.get('intent')})")
            )
            print(
                f"{'ok' if rr == 1 and p_k >= 0.5 else '--'} P@{k}={p_k:.2f} RR={rr:.2f} n={len(r['gevonden'])}{route}  {r['vraag']}"
            )
    print()
    for naam, deel in (
        ("afgestemd", [r for r in resultaten if not r["holdout"]]),
        ("holdout", [r for r in resultaten if r["holdout"]]),
        ("alle", resultaten),
    ):
        s = scoor(deel, k)
        print(
            f"{naam:9} {s['aantal']:3} vragen, k={k}: precision@{k}={s['precision_at_k']:.3f} "
            f"recall@{k}={s['recall_at_k']:.3f} MRR={s['mrr']:.3f} "
            f"routering={s['routering']:.3f} gemiddeld getoond={s['gemiddeld_getoond']:.1f}"
        )
    scores = scoor(resultaten, k)
    if a.json:
        Path(a.json).write_text(
            json.dumps({"scores": scores, "resultaten": resultaten}, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    fout = drempelfouten(resultaten, testset)
    for f in fout:
        print(f"FOUT onder de drempel: {f}")
    return 1 if fout else 0


if __name__ == "__main__":
    sys.exit(main())
