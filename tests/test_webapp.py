"""Network-isolated loopback UI regression checks. No real Nebius inference."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from src.safety_shift import fixture
from src.webapp import Handler, POLICY


class TestLocalReviewConsole(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def get(self, route):
        req = urllib.request.Request(self.base + route)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers, r.read()

    def post(self, path, data: bytes, headers=None):
        h = {"Content-Type": "application/json", **(headers or {})}
        req=urllib.request.Request(self.base + path, method="POST", data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as err:
            try:
                return err.code, json.loads(err.read())
            finally:
                err.close()

    def test_chat_open_tracking_query_preserves_local_static_assets(self):
        for route in ("/?utm_source=chatgpt.com",
                      "/app.js?utm_source=chatgpt.com",
                      "/style.css?utm_source=chatgpt.com"):
            with self.subTest(route=route):
                status,_,body=self.get(route)
                self.assertEqual(status,200)
                self.assertGreater(len(body),100)

    def test_provider_api_get_with_query_rejected(self):
        request=urllib.request.Request(self.base+"/api/fixture?utm_source=chatgpt.com")
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(request,timeout=5)
        self.assertEqual(e.exception.code,400)
        e.exception.close()

    def test_dns_rebinding_host_rejected_before_body(self):
        req=urllib.request.Request(self.base+"/api/fixture",
                                   headers={"Host":"untrusted.example"})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req,timeout=5)
        self.assertEqual(e.exception.code,403)
        e.exception.close()
        data=json.dumps({"mode":"synthetic","case":fixture()}).encode()
        status,body=self.post("/api/triage",data,
                              headers={"Host":"untrusted.example"})
        self.assertEqual(status,403)
        self.assertEqual(body["error"],"HOST_DENIED")

    def test_unknown_query_route_not_opened(self):
        request=urllib.request.Request(self.base+"/../../../.env?utm_source=chatgpt.com")
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(request,timeout=5)
        self.assertEqual(e.exception.code,404)
        e.exception.close()

    def test_handoff_catalogue_exposes_no_private_runbooks(self):
        status,headers,raw=self.get("/api/handoffs")
        self.assertEqual(status,200)
        doc=json.loads(raw)
        self.assertEqual(doc["source_truth"],"ORIGINAL_SYNTHETIC_RUNBOOK_AND_SIGNALS")
        self.assertEqual(doc["model"],"nvidia/Nemotron-3_5-Lightning")
        self.assertEqual(doc["real_calls"],0)
        self.assertFalse(doc["provider_ready"])
        self.assertEqual(len(doc["scenarios"]),3)
        self.assertTrue(all("case" not in s and "runbook" not in s
                            for s in doc["scenarios"]))

    def test_all_synthetic_handoffs_through_http(self):
        from src.handoff_agent import handoff_catalogue
        for item in handoff_catalogue():
            with self.subTest(scene=item["id"]):
                payload=json.dumps({"mode":"synthetic",
                                    "scenario_id":item["id"]}).encode()
                status,value=self.post("/api/handoff",payload)
                self.assertEqual(status,200,value)
                self.assertEqual(value["mode"],"SYNTHETIC_MULTI_TOOL_REPLAY_NO_NEBIUS")
                self.assertEqual(len(value["agent_steps"]),5)
                self.assertEqual(value["provider_api_calls"],0)
                self.assertFalse(value["provider_verified"])
                self.assertFalse(value["automatic_equipment_actions"])
                self.assertTrue(value["human_approval_required"])

    def test_provider_model_denied_without_credit_or_credentials(self):
        from unittest.mock import patch
        import os
        payload=json.dumps({"mode":"provider","scenario_id":"handoff-airflow"}).encode()
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"",
                "NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"}):
            status,value=self.post("/api/handoff",payload)
        self.assertEqual(status,422)
        self.assertEqual(value["error"],"INVALID_OR_BLOCKED_INPUT")

    def test_handoff_bad_origin_and_host_denied(self):
        payload=json.dumps({"mode":"synthetic","scenario_id":"handoff-airflow"}).encode()
        status,value=self.post("/api/handoff",payload,
                   headers={"Origin":"https://adversary.example"})
        self.assertEqual(status,403)
        status,value=self.post("/api/handoff",payload,
                   headers={"Host":"adversary.example"})
        self.assertEqual(status,403)

    def test_handoff_query_and_bad_request_shapes_denied(self):
        inputs=[
           {"mode":"synthetic","scenario_id":"handoff-airflow","approve":True},
           {"mode":"synthetic","scenario_id":"../../private"},
           {"mode":"pay","scenario_id":"handoff-airflow"},
           {"mode":"synthetic","case":{"name":"secret"}},
           {"mode":"synthetic","scenario_id":None}
        ]
        for bad in inputs:
            with self.subTest(bad=bad):
                status,value=self.post("/api/handoff",json.dumps(bad).encode())
                self.assertEqual(status,422)
                self.assertNotIn("NEBIUS_API_KEY",str(value))
        status,value=self.post("/api/handoff?credit=yes",
              b'{}')
        self.assertEqual(status,404)

    def test_handoff_page_has_distinct_source_truth_panels(self):
        status,headers,html=self.get("/")
        self.assertEqual(status,200)
        self.assertIn(b'id="handoff-workbench"',html)
        self.assertIn(b'id="handoff-live"',html)
        self.assertIn(b"NO MACHINE WRITES",html)
        status,headers,script=self.get("/app.js")
        self.assertEqual(status,200)
        self.assertIn(b"/api/handoffs",script)
        self.assertIn(b"/api/handoff",script)
        self.assertIn(b"SYNTHETIC_MULTI_TOOL_REPLAY_NO_NEBIUS",script)

    def test_static_tracking_url_remains_valid_for_new_page(self):
        status,headers,html=self.get("/?utm_source=chatgpt.com")
        self.assertEqual(status,200)
        self.assertIn(b'id="handoff-workbench"',html)

    def test_index_served_with_csp(self):
        status, headers, body=self.get("/")
        self.assertEqual(status,200)
        self.assertIn("SYNTHETIC DEMO",body.decode())
        self.assertEqual(headers.get("Content-Security-Policy"),POLICY)
        self.assertEqual(headers.get("Cache-Control"),"no-store")

    def test_bundled_javascript_no_external_dependency(self):
        status,headers,body=self.get("/app.js")
        self.assertEqual(status,200)
        self.assertIn("fetch('/api/triage'",body.decode())
        self.assertNotIn("https://",body.decode())
        self.assertNotIn("localStorage",body.decode())

    def test_fixture_get(self):
        status,_,body=self.get("/api/fixture")
        self.assertEqual(status,200)
        doc=json.loads(body)
        self.assertEqual(doc["provenance"],"SYNTHETIC_FIXTURE_ONLY")
        self.assertEqual(doc["case"]["setting"],"synthetic")

    def test_safe_mock_path(self):
        status,data=self.post("/api/triage",json.dumps({"mode":"synthetic","case":fixture()}).encode())
        self.assertEqual(status,200)
        self.assertEqual(data["mode"],"SYNTHETIC_OFFLINE_MOCK")
        self.assertFalse(data["provider_verified"])
        self.assertTrue(data["output"]["human_approval_required"])
        self.assertFalse(data["output"]["automatic_equipment_actions"])

    def test_real_path_fail_closed_without_credentials(self):
        # Never set credential or permission variables in this test environment.
        from unittest.mock import patch
        import os
        with patch.dict(os.environ,{"NEBIUS_API_KEY":"","NEBIUS_SANDBOX_ZERO_SPEND_APPROVED":"NO"}):
            status,data=self.post("/api/triage",json.dumps({"mode":"provider","case":fixture()}).encode())
        self.assertEqual(status,422)
        self.assertEqual(data["error"],"INVALID_OR_BLOCKED_INPUT")

    def test_reject_non_synthetic(self):
        case=dict(fixture(),setting="live-equipment")
        status,data=self.post("/api/triage",json.dumps({"mode":"synthetic","case":case}).encode())
        self.assertEqual(status,422)

    def test_reject_origin(self):
        data=json.dumps({"mode":"synthetic","case":fixture()}).encode()
        status,doc=self.post("/api/triage",data,headers={"Origin":"https://adversary.example"})
        self.assertEqual(status,403)
        self.assertEqual(doc["error"],"ORIGIN_DENIED")

    def test_accept_same_origin(self):
        data=json.dumps({"mode":"synthetic","case":fixture()}).encode()
        status,doc=self.post("/api/triage",data,headers={"Origin":self.base})
        self.assertEqual(status,200)
        self.assertFalse(doc["provider_verified"])

    def test_reject_bad_content_type(self):
        data=b"{}"
        status,doc=self.post("/api/triage",data,headers={"Content-Type":"text/plain"})
        self.assertEqual(status,415)

    def test_reject_oversize(self):
        status,doc=self.post("/api/triage",b"x"*4300)
        self.assertEqual(status,413)
        self.assertEqual(doc["error"],"BODY_SIZE_DENIED")

    def test_unknown_endpoint_does_not_read_files(self):
        req=urllib.request.Request(self.base+"/../../.git/config")
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req,timeout=5)
        self.assertEqual(err.exception.code,404)
        err.exception.close()

    def test_no_cors_preflight(self):
        req=urllib.request.Request(self.base+"/api/triage",method="OPTIONS")
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req,timeout=5)
        self.assertEqual(err.exception.code,405)
        err.exception.close()


if __name__=="__main__":
    unittest.main()
