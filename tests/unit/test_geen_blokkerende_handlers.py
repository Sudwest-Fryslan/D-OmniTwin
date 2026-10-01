"""Geen synchrone databasecalls op de event loop (#68, #203).

Een `async def`-route draait op de event loop: een synchrone databasequery daarin
houdt alle andere verzoeken vast. Regel: een route is `def` (FastAPI draait hem
dan in de threadpool), tenzij hij echt iets `await`; synchroon werk gaat dan via
`run_in_threadpool`.
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROUTERS = Path(__file__).resolve().parents[2] / "src" / "omnitwin" / "routers"


def _is_route(node) -> bool:
    for d in node.decorator_list:
        f = d.func if isinstance(d, ast.Call) else d
        if isinstance(f, ast.Attribute) and f.attr in {"get", "post", "put", "patch", "delete"}:
            return True
    return False


def test_async_routes_awaiten_iets():
    fout = []
    for pad in sorted(ROUTERS.glob("*.py")):
        for node in ast.parse(pad.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.AsyncFunctionDef) and _is_route(node):
                if not any(isinstance(x, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for x in ast.walk(node)):
                    fout.append(f"{pad.name}:{node.lineno} {node.name}")
    assert not fout, f"async def zonder await (maak er def van): {fout}"
