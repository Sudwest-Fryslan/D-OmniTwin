"""
Grenzen voor anonieme verzoeken (#203): rate limiting in de app.

Waarom in de app en niet in Traefik: de inlogbeperking telt per IP-adres én
gebruikersnaam (die staat in het formulier, dat ziet Traefik niet), en zo werkt
het ook zonder Traefik (`python run_dev.py`) en achter een eigen proxy. Eén
eenvoudig mechanisme voor beide, zonder extra afhankelijkheid.

Beperkingen: de tellers staan in het geheugen van één proces. Met meerdere
uvicorn-workers telt elke worker apart (de grens wordt dan workers × limiet),
en een herstart zet ze op nul. Voor deze schaal is dat goed genoeg.

IP-adres (#264): `client_ip` is de enige plek waar het adres van de bezoeker
bepaald wordt; de rate limiting en de logmiddleware gebruiken allebei deze functie.
Achter Traefik is het directe adres (de peer) dat van Traefik. X-Forwarded-For wordt
alleen gelezen als de peer in TRUSTED_PROXIES staat (standaard loopback en de
privé-reeksen, zie omnitwin.config). Dan geldt het meest rechtse adres in de keten
dat níet vertrouwd is: dat heeft de buitenste vertrouwde proxy gezien. Alles links
daarvan kan de client zelf meesturen. Anders, of als de header ontbreekt of onzin
bevat, geldt het peer-adres.
"""

from __future__ import annotations

import ipaddress
import math
import threading
import time
from collections import deque
from collections.abc import Callable
from functools import lru_cache
from typing import Union

from fastapi import HTTPException, Request

from omnitwin.config import instellingen


class Limiet:
    """Schuivend venster: hoogstens `maximum` gebeurtenissen per `venster` seconden per sleutel."""

    MAX_SLEUTELS = 10_000  # daarboven worden verlopen sleutels opgeruimd

    def __init__(self, maximum: int, venster: float, klok: Callable[[], float] = time.monotonic):
        self.maximum = maximum
        self.venster = venster
        self._klok = klok
        self._tijden: dict[str, deque[float]] = {}
        self._slot = threading.Lock()

    def _opschonen(self, sleutel: str, nu: float) -> deque[float]:
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


_Netwerk = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@lru_cache(maxsize=8)
def vertrouwde_proxies(lijst: str) -> tuple[_Netwerk, ...]:
    """TRUSTED_PROXIES als netwerken. Ongeldige onderdelen worden overgeslagen."""
    netwerken = []
    for deel in lijst.split(","):
        deel = deel.strip()
        if not deel:
            continue
        try:
            netwerken.append(ipaddress.ip_network(deel, strict=False))
        except ValueError:
            continue
    return tuple(netwerken)


def _als_ip(adres: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address] | None:
    try:
        ip = ipaddress.ip_address(adres.strip())
    except ValueError:
        return None
    # IPv4 in IPv6 (::ffff:1.2.3.4) als IPv4 behandelen
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return ip.ipv4_mapped
    return ip


def _vertrouwd(ip, netwerken: tuple[_Netwerk, ...]) -> bool:
    return ip is not None and any(ip.version == n.version and ip in n for n in netwerken)


def bepaal_client_ip(peer: str, forwarded_for: list[str], trusted_proxies: str) -> str:
    """Kern van `client_ip`, los van het verzoek (testbaar).

    peer: het directe adres van de TCP-verbinding. forwarded_for: alle
    X-Forwarded-For-headers, in volgorde. trusted_proxies: de ruwe TRUSTED_PROXIES.
    """
    netwerken = vertrouwde_proxies(trusted_proxies)
    if not _vertrouwd(_als_ip(peer), netwerken):
        return peer
    hops = [h.strip() for header in forwarded_for for h in header.split(",")]
    hops = [h for h in hops if h]
    for hop in reversed(hops):
        ip = _als_ip(hop)
        if ip is None:
            return peer  # onleesbare waarde: niet raden
        if not _vertrouwd(ip, netwerken):
            return str(ip)
    # Alleen vertrouwde adressen (of geen header): het verste adres in de keten
    return str(_als_ip(hops[0])) if hops else peer


def client_ip(request: Request) -> str:
    """IP-adres van de bezoeker (zie de modulebeschrijving)."""
    peer = request.client.host if request.client else "onbekend"
    return bepaal_client_ip(peer, request.headers.getlist("x-forwarded-for"), instellingen().trusted_proxies)


def te_veel(wachttijd: int, melding: str) -> HTTPException:
    return HTTPException(status_code=429, detail=melding, headers={"Retry-After": str(wachttijd)})


# ── LLM-routes: chat en AI-teksten (narratives) ───────────────────────────────
_llm_limieten: dict[int, Limiet] = {}


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


# ── Terugmeldvoorziening: POST /api/meldingen (#311) ───────────────────────────
_meldingen_limiet = Limiet(maximum=10, venster=60.0)


def beperk_meldingen(request: Request) -> None:
    """Dependency voor POST /api/meldingen: max 10 verzoeken per minuut per IP (in-memory)."""
    wacht = _meldingen_limiet.probeer(client_ip(request))
    if wacht:
        raise te_veel(wacht, f"Te veel meldingen verstuurd. Probeer het over {wacht} seconden opnieuw.")


# ── Eigen buurt via adres of locatie: POST /api/locatie/buurt (#336) ───────────
_locatie_limiet = Limiet(maximum=30, venster=60.0)


def beperk_locatie(request: Request) -> None:
    """Dependency voor POST /api/locatie/buurt: max 30 verzoeken per minuut per IP (PDOK netjes gebruiken)."""
    wacht = _locatie_limiet.probeer(client_ip(request))
    if wacht:
        raise te_veel(wacht, f"Te veel zoekopdrachten. Probeer het over {wacht} seconden opnieuw.")
