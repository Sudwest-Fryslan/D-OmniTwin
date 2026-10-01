"""
Grenzen voor anonieme verzoeken (#203): rate limiting in de app.

Waarom in de app en niet in Traefik: de inlogbeperking telt per IP-adres én
gebruikersnaam (die staat in het formulier, dat ziet Traefik niet), en zo werkt
het ook zonder Traefik (`python run_dev.py`) en achter een eigen proxy. Eén
eenvoudig mechanisme voor beide, zonder extra afhankelijkheid.

Beperkingen: de tellers staan in het geheugen van één proces. Met meerdere
uvicorn-workers telt elke worker apart (de grens wordt dan workers × limiet),
en een herstart zet ze op nul. Voor deze schaal is dat goed genoeg.

IP-adres: achter Traefik is het directe adres dat van Traefik. Dan geldt het
laatste adres in X-Forwarded-For (dat zet de dichtstbijzijnde proxy; eerdere
adressen kan de client zelf meesturen). De header wordt alleen vertrouwd als het
verzoek van een privé- of loopback-adres komt (Docker-netwerk, eigen proxy).
"""

from __future__ import annotations

import ipaddress
import math
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict

from fastapi import HTTPException, Request

from omnitwin.config import instellingen


class Limiet:
    """Schuivend venster: hoogstens `maximum` gebeurtenissen per `venster` seconden per sleutel."""

    MAX_SLEUTELS = 10_000  # daarboven worden verlopen sleutels opgeruimd

    def __init__(self, maximum: int, venster: float, klok: Callable[[], float] = time.monotonic):
        self.maximum = maximum
        self.venster = venster
        self._klok = klok
        self._tijden: Dict[str, Deque[float]] = {}
        self._slot = threading.Lock()

    def _opschonen(self, sleutel: str, nu: float) -> Deque[float]:
        tijden = self._tijden.get(sleutel)
        if tijden is None:
            return deque()
        while tijden and tijden[0] <= nu - self.venster:
            tijden.popleft()
        if not tijden:
            del self._tijden[sleutel]
        return tijden

    def _ruim_op(self, nu: float) -> None:
        if len(self._tijden) > self.MAX_SLEUTELS:
            for sleutel in list(self._tijden):
                self._opschonen(sleutel, nu)

    def wachttijd(self, sleutel: str) -> int:
        """0 als er nog ruimte is, anders het aantal seconden tot er weer ruimte is."""
        with self._slot:
            nu = self._klok()
            tijden = self._opschonen(sleutel, nu)
            if len(tijden) < self.maximum:
                return 0
            return max(1, math.ceil(tijden[0] + self.venster - nu))

    def registreer(self, sleutel: str) -> None:
        with self._slot:
            nu = self._klok()
            self._ruim_op(nu)
            self._tijden.setdefault(sleutel, deque()).append(nu)

    def probeer(self, sleutel: str) -> int:
        """Registreer als er ruimte is (geeft 0), anders de wachttijd in seconden."""
        with self._slot:
            nu = self._klok()
            tijden = self._opschonen(sleutel, nu)
            if len(tijden) >= self.maximum:
                return max(1, math.ceil(tijden[0] + self.venster - nu))
            self._ruim_op(nu)
            self._tijden.setdefault(sleutel, deque()).append(nu)
            return 0

    def reset(self, sleutel: str) -> None:
        with self._slot:
            self._tijden.pop(sleutel, None)


def _privé(adres: str) -> bool:
    try:
        ip = ipaddress.ip_address(adres)
    except ValueError:
        return adres in ("testclient", "localhost")
    return ip.is_private or ip.is_loopback


def client_ip(request: Request) -> str:
    """IP-adres van de bezoeker (zie de modulebeschrijving)."""
    direct = request.client.host if request.client else "onbekend"
    doorgestuurd = request.headers.get("x-forwarded-for")
    if doorgestuurd and _privé(direct):
        laatste = doorgestuurd.split(",")[-1].strip()
        if laatste:
            return laatste
    return direct


def te_veel(wachttijd: int, melding: str) -> HTTPException:
    return HTTPException(status_code=429, detail=melding, headers={"Retry-After": str(wachttijd)})


# ── LLM-routes: chat en AI-teksten (narratives) ───────────────────────────────
_llm_limieten: Dict[int, Limiet] = {}


def _llm_limiet(maximum: int) -> Limiet:
    # Eén limiet per ingestelde waarde, zodat een gewijzigde LLM_RATE_LIMIT (tests) direct geldt
    if maximum not in _llm_limieten:
        _llm_limieten[maximum] = Limiet(maximum, 60.0)
    return _llm_limieten[maximum]


def beperk_llm(request: Request) -> None:
    """Dependency voor routes die een taalmodel aanroepen: LLM_RATE_LIMIT per minuut per IP."""
    maximum = instellingen().llm_rate_limit
    if maximum <= 0:
        return
    wacht = _llm_limiet(maximum).probeer(client_ip(request))
    if wacht:
        raise te_veel(wacht, f"Te veel verzoeken. Probeer het over {wacht} seconden opnieuw.")
