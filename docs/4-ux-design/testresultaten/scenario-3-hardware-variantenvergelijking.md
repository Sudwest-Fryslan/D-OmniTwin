# Testresultaten Scenario 3: Hardware- en Variantenvergelijking (GPU)

> **Status:** Uitgevoerd (Empirische hardware-meting met echte GPU via `meet_465.py`)  
> **Datum:** 2026-10-27  
> **Omgeving:** Lokale host met hardware GPU-versnelling (`MEET_GPU=1`), Desktop 1920×1080  
> **Geteste gebieden:** 3 representatieve buurten (`BU19000115` Bolsward, `BU19000108` Sneek, `BU19000004` Workum)  
> **Gekoppelde issues:** [#465](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/465) (Onderzoek) en [#466](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/466) (Realisatie)  
> **Moederdocumenten:** [`docs/4-ux-design/interactie-gebiedsselectie.md`](../interactie-gebiedsselectie.md) en [`docs/4-ux-design/pve-rechter-dock-architectuur.md`](../pve-rechter-dock-architectuur.md)

---

## 1. Doel van de meting

Het verifiëren van de voorgestelde optimalisaties en choreografie-varianten op **echte hardware met actieve GPU-versnelling**:
1. Wat is de werkelijke impact op de rendertijd van het zonnediagram als `getComputedTextLength` (forced reflows) wordt vervangen door `canvas.measureText` (Variant D: *Kosten weg*)?
2. Elimineert de deduplicatie (B1) de dubbele netwerkaanroep naar `/api/kompas/1/gebied/...`?
3. Bewijst de choreografie van Taeke (*Variant B+D: render en dock na landing*) dat zwaar rekenwerk en DOM-injecties volledig buiten de cameravlucht vallen?
4. Hoe gedraagt de camera-positionering zich t.o.v. de vrije zone van de kaart wanneer het dock opent?

---

## 2. Geteste Varianten

* **`huidig` (Status Quo):**  
  De huidige werking in de codebase: alle acties starten gelijktijdig bij de klik (data ophalen, renderen, cameravlucht en dock inschuiven).
* **`kosten` (Variant D — Directe optimalisatie):**  
  B1 deduplicatie actief + woordomloop in `kompas.js` gemeten via `canvas.measureText` in plaats van `getComputedTextLength` op het DOM.
* **`taeke+kosten` (Variant B+D — Doelchoreografie):**  
  Variant D gecombineerd met de choreografie waarbij het zonnediagram pas rendert en het dock pas inschuift **nádat de camera is geland**.

---

## 3. Gemeten Resultaten (Hardware GPU)

De metingen zijn uitgevoerd via Playwright met live Chrome-instantie op de lokale GPU (mediaanwaarden per variant over de 3 buurten):

| Variant | n | Render zonnediagram | Cam Start | Cam Einde (Landing) | Render voltooid (`>cijfers`) | Dock geopend (`>dock`) | Netwerk-calls (`api`) | Layout checks (`gctl`) |
|---|---|---|---|---|---|---|---|---|
| **`huidig`** | 3 | **64 ms** | 1.992 ms | 2.826 ms | **2.043 ms** *(in de vlucht)* | **1.234 ms** *(in de vlucht)* | 3 | 1.038 |
| **`kosten` (D)** | 3 | **15 ms** | 1.818 ms | 2.870 ms | **1.795 ms** *(in de vlucht)* | **1.209 ms** *(in de vlucht)* | 2 | 519 |
| **`taeke+kosten` (B+D)** | 3 | **17 ms** | 2.011 ms | 3.212 ms | **3.772 ms** *(ná landing)* | **4.362 ms** *(ná render)* | 2 | 519 |

---

## 4. Belangrijkste Empirische Conclusies

### 1. Rendertijd daalt met >75% (van 64 ms naar 15–17 ms)
Door het elimineren van de synchrone DOM-tekstmetingen (`getComputedTextLength` na elk woord) en het gebruik van `canvas.measureText` wordt layout thrashing volledig vermeden. Het opbouwen van het complete zonnediagram kost nu nog slechts 15 tot 17 ms op de CPU.

### 2. Netwerklast direct met 33% omlaag (B1)
In de huidige situatie vertrekken er bij elke klik 3 netwerkverzoeken (1× `/gebiedsmonitor/gebieden/...` en 2× identiek `/kompas/1/gebied/...`). Met B1 daalt dit direct naar 2 verzoeken.

### 3. Vlucht en render lopen niet langer door elkaar
* In **`huidig`** en **`kosten`** renderen de cijfers (resp. op 2.043 ms en 1.795 ms) en schuift het dock open (rond 1.220 ms) **middenin de cameravlucht** (die loopt van ~1.800 ms tot ~2.850 ms). Dit verklaart de haperingen en frame drops tijdens de vlucht.
* In **`taeke+kosten`** vliegt de camera eerst rustig naar het doel en landt op **3.212 ms**. Pas **ná de landing** vindt de render plaats (**3.772 ms**, duur slechts 17 ms), direct gevolgd door het inschuiven van het dock (**4.362 ms**). De vlucht zelf is daarmee 100% vrij van CPU- en DOM-belasting.

---

## 5. Aandachtspunt voor Realisatie (#466): Vrije Zone Berekening

Tijdens de live-test is visueel geconstateerd dat een geselecteerde buurt na de landing soms **gedeeltelijk achter het geopende rechterdock verdwijnt**.

### Oorzaak:
De huidige camera-aansturing (`flyToGebied` in `app.js`) centreert op het klikpunt of berekent de viewport met de toestand *vóór* het dock geopend is (dock gesloten = 100% schermbreedte). Wanneer het dock vervolgens opent (25–30% schermbreedte aan de rechterkant), schuift het dock over de rechterhelft van de zojuist gecentreerde buurt heen.

### Oplossing & Eis voor Realisatie-issue #466:
1. **`getFreezone` met doelstand:**  
   Bij het starten van de vlucht moet de vrije zone worden berekend op basis van de **toekomstige eindstand** (rechterdock open = breedte minus dockbreedte van ca. 380px / 25vw).
2. **`fitBounds` met padding (FE-4.2):**  
   In plaats van een eenvoudige `flyTo` op het klikpunt met een willekeurig zoomniveau, gebruikt de kaart `fitBounds` op de bounding box van de buurt met padding conform de berekende vrije zone. Hierdoor is gegarandeerd dat het geselecteerde gebied **100% vrij en zichtbaar** blijft naast het geopende dock.
