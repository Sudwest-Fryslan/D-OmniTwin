"""
Profiel definities: een bestaande UUID met een andere naam volgt de bron, met een waarschuwing in het log
(hergebruikte UUID's in de monitor, #340). Met een nep-cursor, zonder database.
"""

import logging

import pytest

from omnitwin.laden import p_definities as pdef
from omnitwin.laden.basis import Context

pytestmark = pytest.mark.unit

UUID = "0e5b1c4a-1111-4aaa-8aaa-000000000001"


class NepCursor:
    def __init__(self):
        self.sql, self.rowcount, self._laatste = [], 0, ""

    def execute(self, sql, params=None):
        self.sql.append(sql)
        self._laatste = sql

    def fetchone(self):
        return {"n": 0}

    def fetchall(self):
        if "IS DISTINCT FROM i.naam" in self._laatste:
            return [{"uuid": UUID, "oud": "Inwoners 0-14 jaar", "nieuw": "Inwoners 0-17 jaar"}]
        return []


def test_andere_naam_geeft_waarschuwing_en_volgt_de_bron(caplog):
    cur = NepCursor()
    ctx = Context(levering={"id": 7}, dataset={"id": "voorbeeld-definities", "laadprofiel": {}})
    with caplog.at_level(logging.WARNING, logger="omnitwin.laden.definities"):
        pdef.publiceer(cur, ctx)
    melding = [r.getMessage() for r in caplog.records if r.name == "omnitwin.laden.definities"]
    assert len(melding) == 1 and UUID in melding[0] and "'Inwoners 0-14 jaar' wordt 'Inwoners 0-17 jaar'" in melding[0]
    # de controle staat vóór de update die de naam overschrijft
    i_controle = next(i for i, s in enumerate(cur.sql) if "IS DISTINCT FROM i.naam" in s)
    i_update = next(i for i, s in enumerate(cur.sql) if "UPDATE public.indicatoren i SET" in s and "naam = s.naam" in s)
    assert i_controle < i_update
