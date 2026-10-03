"""
Soort omgeving (#245): `OMNITWIN_OMGEVING=productie|test|demo`, standaard productie.

- **demo**: standaardaccounts met bekende wachtwoorden, zodat iedereen kan proberen in te loggen:
  in Keycloak (realm omnitwin) `admin`/`admin` (realm-rollen beheerder en gebruikersbeheerder) en
  `gebruiker`/`gebruiker` (lezer), met een versoepeld wachtwoordbeleid; lokaal (zonder Keycloak) de
  beheerder `admin`/`admin` als ADMIN_PASSWORD leeg is. Viewer en beheerscherm tonen een demobalk.
- **test**: geen standaardaccounts; zwakke wachtwoorden geven alleen een waarschuwing.
- **productie**: geen standaardaccounts, en db-init weigert een bekend zwak ADMIN_PASSWORD of
  KEYCLOAK_ADMIN_PASSWORD (exitcode 1, `python -m omnitwin.omgeving controleer`).

De Keycloak-accounts zet `python -m omnitwin.omgeving keycloak` (compose-service `keycloak-demo`,
profiel keycloak) bij elke start, idempotent:
- demo: beleid versoepelen, accounts aanmaken of herstellen (wachtwoord, rollen, aan);
- anders: demo-accounts (herkenbaar aan voornaam `Demo` en achternaam `DEMO_ACHTERNAAM`) verwijderen en
  het demobeleid terugzetten naar dat uit de realmexport. Een eigen gebruiker `admin` of `gebruiker`
  (zonder dat kenmerk) blijft altijd ongemoeid.

De demowachtwoorden staan bewust in de code: ze zijn publiek en worden alleen bij demo gezet.
Toegang tot de admin-API van Keycloak zoals bij de testaccounts (`omnitwin.testaccounts`):
KEYCLOAK_ADMIN_PASSWORD (tijdelijke beheerder van realm master) of een service account.
"""

from __future__ import annotations

import sys
import time

from omnitwin.config import instellingen

# Bekende zwakke wachtwoorden (kleine letters). Een wachtwoord gelijk aan de gebruikersnaam of korter
# dan MIN_LENGTE is ook zwak.
ZWAK = frozenset({
    "admin", "administrator", "beheer", "beheerder", "gebruiker", "demo", "test", "testen",
    "password", "passwd", "wachtwoord", "geheim", "secret", "welkom", "welcome", "changeme", "letmein",
    "qwerty", "azerty", "123456", "1234567", "12345678", "123456789", "1234567890", "000000",
    "omnitwin", "d-omnitwin", "keycloak", "postgres", "root", "toor",
})
MIN_LENGTE = 8

# Demo-accounts in Keycloak: naam -> (wachtwoord, realm-rollen). Bewust publiek, alleen bij demo.
DEMO_ACCOUNTS = {
    "admin": ("admin", ("beheerder", "gebruikersbeheerder")),
    "gebruiker": ("gebruiker", ("lezer",)),
}
DEMO_VOORNAAM = "Demo"
DEMO_ACHTERNAAM = "D-OmniTwin demo"   # geen leestekens: Keycloak weigert die in namen
DEMO_BELEID = "length(5)"
# Beleid uit deploy/keycloak/realm-omnitwin.json (tests/unit/test_omgeving.py houdt ze gelijk)
STANDAARD_BELEID = "length(12) and notUsername and notEmail"


class OmgevingFout(Exception):
    """Installatie geweigerd (productie met een zwak wachtwoord) of Keycloak weigert."""


def is_zwak(wachtwoord: str | None, gebruikersnaam: str | None = None) -> bool:
    """Bekend zwak, gelijk aan de gebruikersnaam of korter dan MIN_LENGTE. Leeg is niet zwak
    (dan genereert db-init een wachtwoord, of is Keycloak uit)."""
    w = (wachtwoord or "").strip()
    if not w:
        return False
    return (w.lower() in ZWAK or len(w) < MIN_LENGTE
            or bool(gebruikersnaam and w.lower() == gebruikersnaam.strip().lower()))


def zwakke_instellingen(omgeving: dict[str, str]) -> list[str]:
    """Namen van de variabelen met een zwak wachtwoord (geen waarden: die horen niet in de log)."""
    zwak = []
    if is_zwak(omgeving.get("ADMIN_PASSWORD"), omgeving.get("ADMIN_USER") or "admin"):
        zwak.append("ADMIN_PASSWORD")
    if is_zwak(omgeving.get("KEYCLOAK_ADMIN_PASSWORD"), "admin"):
        zwak.append("KEYCLOAK_ADMIN_PASSWORD")
    return zwak


def controleer_installatie(omgeving: dict[str, str] | None = None) -> list[str]:
    """Meldingen voor db-init. Productie met een zwak wachtwoord: OmgevingFout."""
    import os
    env = dict(os.environ) if omgeving is None else omgeving
    soort = instellingen().omgeving if omgeving is None else _soort(env.get("OMNITWIN_OMGEVING", ""))
    zwak = zwakke_instellingen(env)
    if zwak and soort == "productie":
        raise OmgevingFout(
            f"{', '.join(zwak)} is een bekend of te zwak wachtwoord (minimaal {MIN_LENGTE} tekens, niet "
            "gelijk aan de gebruikersnaam). Dat wordt geweigerd bij OMNITWIN_OMGEVING=productie (de "
            "standaard). Kies een sterk wachtwoord (openssl rand -hex 24), of laat ADMIN_PASSWORD leeg "
            "(dan wordt er een gegenereerd). Alleen om te proberen: OMNITWIN_OMGEVING=demo.")
    meldingen = [f"Omgeving: {soort}"]
    if zwak:
        meldingen.append(f"Waarschuwing: zwak wachtwoord in {', '.join(zwak)} (toegestaan bij {soort}).")
    return meldingen


def _soort(waarde: str) -> str:
    from omnitwin.config import _omgeving
    return _omgeving(waarde)


def lokaal_admin_wachtwoord(admin_password: str | None, soort: str) -> str | None:
    """Wachtwoord voor de lokale beheerder bij de eerste init: in demo zonder ADMIN_PASSWORD `admin`,
    anders ongewijzigd (None/leeg = db-init genereert er een)."""
    if soort == "demo" and not (admin_password or "").strip():
        return DEMO_ACCOUNTS["admin"][0]
    return admin_password


# ------------------------------------------------------------------ Keycloak

def is_demo_account(rep: dict) -> bool:
    return rep.get("firstName") == DEMO_VOORNAAM and rep.get("lastName") == DEMO_ACHTERNAAM


def _zoek(beheer, naam: str) -> dict | None:
    r = beheer._verzoek("GET", "/users", params={"username": naam, "exact": "true"})
    return next((u for u in r.json() if u.get("username") == naam), None)


def pas_toe_in_keycloak(beheer, soort: str) -> list[str]:
    """Zet de demo-accounts (soort demo) of ruim ze op (anders). `beheer` is een
    `testaccounts.KeycloakBeheer` (of een nep-object met `_verzoek`). Geeft meldingen zonder geheimen."""
    meldingen = []
    realm = beheer._verzoek("GET", "").json()
    beleid = realm.get("passwordPolicy") or ""
    if soort == "demo":
        if beleid != DEMO_BELEID:
            beheer._verzoek("PUT", "", json={"passwordPolicy": DEMO_BELEID})
            meldingen.append(f"wachtwoordbeleid versoepeld voor de demo ({DEMO_BELEID})")
        for naam, (wachtwoord, rollen) in DEMO_ACCOUNTS.items():
            bestaand = _zoek(beheer, naam)
            if bestaand and not is_demo_account(bestaand):
                meldingen.append(f"gebruiker {naam} bestaat al en is geen demo-account: niet aangeraakt")
                continue
            if bestaand is None:
                beheer._verzoek("POST", "/users", json={
                    "username": naam, "enabled": True, "firstName": DEMO_VOORNAAM, "lastName": DEMO_ACHTERNAAM,
                    "email": f"{naam}@demo.example.org", "emailVerified": True, "requiredActions": []})
                bestaand = _zoek(beheer, naam)
                meldingen.append(f"demo-account {naam} aangemaakt ({', '.join(rollen)})")
            else:
                # Volledige representatie terug: een gedeeltelijke kan velden (voornaam e.d.) wissen
                beheer._verzoek("PUT", f"/users/{bestaand['id']}",
                                json={**bestaand, "enabled": True, "requiredActions": []})
                meldingen.append(f"demo-account {naam} bijgewerkt ({', '.join(rollen)})")
            beheer._verzoek("PUT", f"/users/{bestaand['id']}/reset-password",
                            json={"type": "password", "value": wachtwoord, "temporary": False})
            beheer.ken_rollen_toe(bestaand["id"], rollen)
    else:
        for naam in DEMO_ACCOUNTS:
            bestaand = _zoek(beheer, naam)
            if bestaand and is_demo_account(bestaand):
                beheer._verzoek("DELETE", f"/users/{bestaand['id']}")
                meldingen.append(f"demo-account {naam} verwijderd (OMNITWIN_OMGEVING={soort})")
        if beleid == DEMO_BELEID:
            beheer._verzoek("PUT", "", json={"passwordPolicy": STANDAARD_BELEID})
            meldingen.append("wachtwoordbeleid van de demo teruggezet naar dat uit de realmexport")
    return meldingen


def keycloak(pogingen: int = 6, wacht: float = 5.0) -> int:
    from omnitwin.testaccounts import KeycloakBeheer, TestaccountFout
    soort = instellingen().omgeving
    for poging in range(1, pogingen + 1):
        try:
            meldingen = pas_toe_in_keycloak(KeycloakBeheer(), soort)
            break
        except TestaccountFout as e:
            if "HTTP 5" not in str(e) and "admin-token" not in str(e):
                print(f"❌ Demo-accounts in Keycloak: {e}", file=sys.stderr)
                return 1
            fout = e
        except OSError as e:  # requests.ConnectionError e.d.: Keycloak start nog
            fout = e
        if poging == pogingen:
            print(f"❌ Demo-accounts in Keycloak: Keycloak niet bereikbaar ({type(fout).__name__}: {fout})",
                  file=sys.stderr)
            return 1
        time.sleep(wacht)
    print(f"✅ Keycloak, omgeving {soort}: " + ("; ".join(meldingen) if meldingen else "geen demo-accounts, niets te doen"))
    return 0


def main(argv: list[str]) -> int:
    opdracht = argv[1] if len(argv) > 1 else ""
    if opdracht == "controleer":
        try:
            for m in controleer_installatie():
                print(f"   {m}")
        except OmgevingFout as e:
            print(f"❌ {e}", file=sys.stderr)
            return 1
        return 0
    if opdracht == "keycloak":
        return keycloak()
    print("gebruik: python -m omnitwin.omgeving controleer|keycloak", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
