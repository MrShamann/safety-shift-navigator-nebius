"""Read-only loopback web contract for the judge's second evidence action."""
from __future__ import annotations
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from src.webapp import Handler


class EvidenceLoopHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.base="http://127.0.0.1:"+str(cls.server.server_port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def post(self,path,data,headers=None):
        request=urllib.request.Request(
            self.base+path,method="POST",data=json.dumps(data).encode(),
            headers={"Content-Type":"application/json",**(headers or {})}
        )
        try:
            with urllib.request.urlopen(request,timeout=5) as reply:
                return reply.status,json.loads(reply.read())
        except urllib.error.HTTPError as exc:
            try:
                return exc.code,json.loads(exc.read())
            finally:
                exc.close()

    def test_judge_can_inspect_and_reconcile_nine_variants(self):
        for scene in ("handoff-airflow","handoff-access","handoff-network"):
            with self.subTest(scene=scene):
                status,card=self.post("/api/evidence-options",{"scenario_id":scene})
                self.assertEqual(status,200)
                self.assertEqual(len(card["source_options"]),3)
                for option in card["source_options"]:
                    status,result=self.post("/api/reconcile",{
                        "scenario_id":scene,"record_id":option["id"]})
                    self.assertEqual(status,200,result)
                    self.assertEqual(result["provider_api_calls"],0)
                    self.assertFalse(result["provider_verified"])
                    self.assertTrue(result["human_approval_required"])
                    self.assertFalse(result["automatic_equipment_actions"])
                    self.assertEqual(result["attached_record"]["evidence_id"],option["evidence_id"])

    def test_cannot_cross_scene_or_inject_hidden_fields(self):
        for route,body in [
            ("/api/evidence-options",{"scenario_id":"handoff-airflow","admin":"1"}),
            ("/api/reconcile",{"scenario_id":"handoff-access","record_id":"AIR-JOURNAL-01"}),
            ("/api/reconcile",{"scenario_id":"handoff-access","record_id":"ACCESS-CONFLICT-02",
                               "override_approval":True}),
            ("/api/reconcile",{"scenario_id":"handoff-network","record_id":"../../.env"}),
        ]:
            with self.subTest(route=route,body=body):
                status,value=self.post(route,body)
                self.assertEqual(status,422)
                self.assertEqual(value["error"],"INVALID_OR_BLOCKED_INPUT")

    def test_cannot_cross_origin_for_even_offline_record_selection(self):
        status,value=self.post("/api/reconcile",{
            "scenario_id":"handoff-network","record_id":"NETWORK-JOURNAL-01"},
            {"Origin":"https://evil.example"})
        self.assertEqual(status,403)
        self.assertEqual(value["error"],"ORIGIN_DENIED")

    def test_no_hidden_vendor_request_or_body_reflection_on_error(self):
        bad={"scenario_id":"handoff-network","record_id":"NETWORK-CONFLICT-02",
             "token":"should-not-echo"}
        status,value=self.post("/api/reconcile",bad)
        self.assertEqual(status,422)
        self.assertNotIn("should-not-echo",json.dumps(value))
        req=urllib.request.Request(self.base+"/api/evidence-options")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req,timeout=5)
        self.assertEqual(ctx.exception.code,404)
        ctx.exception.close()


if __name__=="__main__":
    unittest.main()
