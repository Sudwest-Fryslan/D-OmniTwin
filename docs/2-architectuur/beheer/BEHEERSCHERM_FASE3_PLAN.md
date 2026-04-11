# Beheerscherm Fase 3 - Implementation Plan (Vervolg)

**Datum:** 03-02-2026  
**Status:** Phase 1 COMPLEET ✅ | Phase 2-4 TODO  
**Resterende Effort:** ~4-5 uur

---

## ✅ COMPLEET: Phase 1 - D3 Collapsible Tree

**Gerealiseerd:**
- `HierarchiePage.tsx` - Volledig functionele D3 tree visualisatie
- Expand/collapse animaties met smooth transitions
- Rechtermuisklik → Details panel met breadcrumb navigatie
- Zoom & pan support via D3 zoom behavior
- Statistieken display (thema's, onderdelen, indicatoren)
- TypeScript compliant, production build succesvol (127 kB JS)

**Locatie:** `admin-panel/src/pages/HierarchiePage.tsx`

---

## 🔜 TODO: Phase 2 - Color Schema Management (2-3 uur)

### Files to Create

#### [NEW] [KleurschemasPage.tsx](file:///mnt/f/VSCode_Projects/D-OmniTwin/admin-panel/src/pages/KleurschemasPage.tsx)

**Features:**
- List existing color schemas with preview swatches
- Create new schema form with color picker (gebruik `<input type="color">`)
- Delete schema (with confirmation modal)
- Preview on sample kompas visualization

**API Endpoints (READY):**
- `GET /api/admin/color-schemas` ✅
- `POST /api/admin/color-schemas` ✅

**Component Structure:**
```tsx
KleurschemasPage
├── SchemaList (grid met color previews)
├── CreateSchemaForm (modal met color pickers)
└── DeleteConfirmation (modal)
```

**Design:**
- Grid layout met schema cards
- Color swatches: 3 kleuren (min, mid, max)
- Inline editing mogelijk maken
- Delete button met confirmation

---

## 🔜 TODO: Phase 3 - Production Build Integration (1 uur)

#### [MODIFY] [main.py](file:///mnt/f/VSCode_Projects/D-OmniTwin/main.py)

**Change:** Serve built admin panel from `/admin` route

```python
from fastapi.staticfiles import StaticFiles

# Mount static files for admin panel (AFTER all API routes!)
app.mount("/admin", StaticFiles(
    directory="admin-panel/build", 
    html=True
), name="admin")
```

**Verification:**
- `npm run build` in `admin-panel/`
- Start FastAPI server
- Browse to `http://localhost:8000/admin`
- Test login, navigatie, Hiërarchie page

---

## 🔜 OPTIONAL: Phase 4 - Klimaat Hierarchy Split (1-2 uur)

**Context:** Thema "Klimaat" splitsen in 3 sub-thema's

**Database Changes:**
- SQL script: 3 nieuwe onderdelen onder "Openbare ruimte"
  - Hemelwater overlast
  - Droogte  
  - Hittestress
- Indicator reassignment (klimaat-gerelateerde indicatoren)

**Files:**
- `data/migrations/split_klimaat_theme.sql` (nieuw)
- Update `schema_latest.sql`

---

## Verification Checklist

### Phase 2
- [ ] Color schemas page toont alle schemas
- [ ] New schema kan worden aangemaakt
- [ ] Color picker works
- [ ] Schema kan worden verwijderd

### Phase 3
- [ ] `/admin` route werkt in productie
- [ ] Static files worden correct geserveerd
- [ ] Login flow werkt
- [ ] Hiërarchie tree render correct

### Phase 4 (Optional)
- [ ] 3 nieuwe onderdelen in database
- [ ] Indicatoren correct toegewezen
- [ ] Tree visualisatie toont nieuwe structuur

---

## Technische Notes

**Admin Panel Stack:**
- React 18 + TypeScript
- React Query (data fetching)
- Zustand (state management)
- D3.js (visualisatie)
- Lucide Icons

**API Authentication:**
- Header-based: `X-Admin-Key` (stored in localStorage)

**Build Process:**
- `npm run build` → `admin-panel/build/`
- FastAPI serves static files from `/admin`

---

## Volgende Sessie - Start Hier

1. **Test D3 Tree in browser** → Navigeer naar `/admin` → Hiërarchie
2. **Start Phase 2** → `KleurschemasPage.tsx` component
3. **Production Integration** → Mount `/admin` in FastAPI

**Geschatte totale tijd restant:** 4-5 uur (zonder Phase 4)
