import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.database import get_db
from services.report_service import ReportDataService
from routers.report import router

class TestDeelgebiedReport(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        self.sample_buurten = ['BU19000101', 'BU19000102', 'BU19000104']

    def test_deelgebied_service_payload(self):
        """Test directe service aanroep voor deelgebiedsanalyse."""
        db = next(get_db())
        svc = ReportDataService(db)

        payload = svc.generate_deelgebied_payload(
            gebied_ids=self.sample_buurten,
            deelgebied_naam="Sneek Test"
        )

        # Basis checks
        self.assertEqual(payload["deelgebied_naam"], "Sneek Test")
        self.assertEqual(payload["totaal_buurten"], 3)
        self.assertEqual(payload["buurten_met_data"], 3)
        self.assertEqual(len(payload["kwadranten"]), 4)

        # Kwadrant volgorde
        kw_names = [k["kwadrant_naam"] for k in payload["kwadranten"]]
        self.assertEqual(kw_names, [
            "Kwaliteit fysieke leefomgeving",
            "Kwaliteit sociale leefomgeving",
            "Kwaliteit van leven",
            "Samenstelling"
        ])

        # Inwoners & weging
        self.assertEqual(payload["methodologie"]["aggregatie"], "gewogen_gemiddelde")
        self.assertGreater(payload["methodologie"]["totaal_inwoners_gebied"], 0)
        self.assertIn("scoringtype_disclaimer", payload["methodologie"])
        self.assertIn("statistisch_effect", payload["methodologie"])

        # Indicatoren en drilldown
        first_kw = payload["kwadranten"][0]
        self.assertGreater(len(first_kw["themas"]), 0)
        first_theme = first_kw["themas"][0]

        all_items = first_theme["top10_aandachtspunten"] + first_theme["top10_kansen"]
        self.assertGreater(len(all_items), 0)

        first_ind = all_items[0]
        self.assertIn("gewogen_waarde", first_ind)
        self.assertIn("ref_gemiddelde", first_ind)
        self.assertIn("z_score", first_ind)
        self.assertIn("buurten_drilldown", first_ind)
        self.assertGreater(len(first_ind["buurten_drilldown"]), 0)

        # Drilldown velden
        first_drill = first_ind["buurten_drilldown"][0]
        self.assertIn("buurt_naam", first_drill)
        self.assertIn("inwoners", first_drill)
        self.assertIn("buurt_z_score", first_drill)
        self.assertIn("verschil", first_drill)

    def test_deelgebied_api_endpoint_success(self):
        """Test POST /api/report/deelgebied HTTP endpoint."""
        res = self.client.post("/api/report/deelgebied", json={
            "gebied_ids": self.sample_buurten,
            "deelgebied_naam": "Sneek Stad",
            "referentie": "gemeente"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["deelgebied_naam"], "Sneek Stad")
        self.assertEqual(data["referentie_modus"], "gemeente")
        self.assertEqual(len(data["kwadranten"]), 4)

    def test_deelgebied_api_endpoint_fryslan_ref(self):
        """Test POST /api/report/deelgebied met referentie Fryslân."""
        res = self.client.post("/api/report/deelgebied", json={
            "gebied_ids": self.sample_buurten,
            "referentie": "fryslan"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["referentie_modus"], "fryslan")
        self.assertIn("Fryslân", data["referentie_label"])

    def test_deelgebied_api_invalid_ids(self):
        """Test POST /api/report/deelgebied met niet-bestaande IDs."""
        res = self.client.post("/api/report/deelgebied", json={
            "gebied_ids": ["ONBEKEND_001"]
        })
        self.assertEqual(res.status_code, 400)

if __name__ == '__main__':
    unittest.main()
