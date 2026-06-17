# Ontwerp & Implementatieplan: E-mail Alerts bij ERROR/CRITICAL logs (Issue #10)

**Doel:** Het systeem moet beheerders automatisch waarschuwen wanneer er zich ernstige fouten (`ERROR` of `CRITICAL`) voordoen in de applicatie, zonder afhankelijk te zijn van één specifieke e-mailprovider.

**Tijdlijn:** Gepland voor ná Sprint 19.

## 1. Flexibele Configuratie (.env)

Om makkelijk te kunnen switchen tussen verschillende providers (Microsoft/Office365, Google/Gmail, of een eigen mailserver) gebruiken we standaard SMTP variabelen in het `.env` bestand. 

```env
# ==========================================
# E-MAIL ALERTS CONFIGURATIE (SMTP)
# ==========================================
LOG_ALERT_ENABLED=true
LOG_ALERT_TO=beheer@jouwdomein.nl

# Voorbeelden van veelgebruikte hosts:
# - Gmail: smtp.gmail.com (Poort 587, TLS=true)
# - Outlook/Office365: smtp.office365.com (Poort 587, TLS=true)
# - Eigen server: mail.jouwdomein.nl

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=alerts@jouwdomein.nl
SMTP_PASS=SuperGeheimAppWachtwoord
SMTP_FROM=alerts@jouwdomein.nl
```

> **Let op:** Zowel Google als Microsoft eisen tegenwoordig vaak het gebruik van "App Passwords" (Applicatiewachtwoorden) als je SMTP gebruikt, vooral wanneer Two-Factor Authentication (2FA) aan staat op het e-mailaccount.

## 2. Architectuur: `log_alert_service.py`

We bouwen een asynchrone service (`services/log_alert_service.py`) die in de achtergrond meeluistert naar inkomende logs.

### A. Debouncing (Anti-Spam)
We willen voorkomen dat de beheerder 100 e-mails per minuut krijgt als de database plat ligt.
- **Logica:** De service houdt een in-memory dictionary bij van de laatste waarschuwingen: `last_alert_time[category]`.
- **Regel:** Er mag per categorie maximaal 1 e-mail per 5 minuten verzonden worden.
- **Verzamel-gedrag:** Als er binnen die 5 minuten meer fouten in dezelfde categorie optreden, worden deze in het geheugen gebufferd en in de volgende "batch" mail meegestuurd, of genegeerd met een melding ("+ 14 andere fouten opgetreden").

### B. Python `aiosmtplib` of `smtplib`
We integreren een robuuste mail-client in Python.
- Bij `SMTP_USE_TLS=true` start de client een `STARTTLS` verbinding.
- Er komt een nette HTML-template voor de e-mail met:
  - **Tijdstip** en **Level** (ERROR / CRITICAL)
  - **Categorie** (Bijv. KAART, DATABASE, API)
  - **Foutmelding** (Exception)
  - Optioneel: Welke gebruiker ingelogd was.

### C. Connectie Test-functie
Om makkelijk te kunnen wisselen van provider, voegen we in het Admin Panel (bij de Log Viewer / Log Config tab) een knop toe: **"Test E-mail Instellingen"**. 
Deze roept een nieuw API endpoint aan (`POST /api/admin/logs/test-alert`) die direct probeert in te loggen op de SMTP server en een testmailtje stuurt. Dit valideert meteen of de switch succesvol was.

## 3. Implementatie Stappen (Todo's)

Wanneer we dit oppakken, volgen we dit stappenplan:

1. **Afhankelijkheden:** Installeer eventueel `aiosmtplib` of standaard `email.message` modules configureren.
2. **Settings:** Pas `config.py` of `.env` parser aan zodat hij de nieuwe `SMTP_` variabelen laadt.
3. **Service:** Schrijf `services/log_alert_service.py`.
4. **Integratie:** Koppel de service aan de bestaande `AsyncLogQueue` in `logging_service.py` (als een extra 'consumer' die op ERROR/CRITICAL triggert).
5. **Endpoint:** Maak de "Test Alert" route in `routers/log_viewer.py`.
6. **Frontend:** Voeg in de beheeromgeving bij "Log Viewer -> Instellingen" inzicht toe over de mail-status (Actief/Inactief) en de Test-knop.

---
*Document opgesteld als technische voorbereiding (Issue #10).*
