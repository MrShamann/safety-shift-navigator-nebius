"""Compile a free, static, truth-labeled judge sandbox from original Python logic.

This is NOT a live Nemotron call. The authenticated original application G1
receipt is retained as a separate evidence tier. Output goes to --target only,
without touching the private repo history, spending credits or using a key.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.handoff_agent import handoff_catalogue,offline_handoff
from src.safety_shift import fixture,offline_triage
from src.evidence_loop import evidence_options,reconcile_evidence


def build(target:Path,receipt:Path)->dict:
    target=target.resolve()
    if target == ROOT or ROOT in target.parents and target.name not in ("judge-site","docs"):
        raise ValueError("refuse to overwrite private source documents")
    if not receipt.is_file() or receipt.is_symlink():
        raise ValueError("redacted G1 receipt must be a regular file")
    sanitized=json.loads(receipt.read_text(encoding="utf-8"))
    if (sanitized.get("verification") !=
            "AUTHENTICATED_NEBIUS_REAL_APPLICATION_API_AND_INDEPENDENT_CRITIC_PASS"
        or sanitized.get("actual_api_calls")!=1
        or sanitized.get("secret_or_card_included") is not False):
        raise ValueError("authentic G1 redacted receipt not verified")
    target.mkdir(parents=True,exist_ok=True)
    data=target/"data"
    data.mkdir(exist_ok=True)
    for name in ("app.js","style.css"):
        shutil.copy2(ROOT/"web"/name,target/name)
    html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
    for original,replacement in (
        ('href="/style.css"','href="./style.css"'),
        ('src="/app.js"','src="./app.js"'),
    ):
        if html.count(original)!=1:raise ValueError("unexpected input asset")
        html=html.replace(original,replacement)
    old='<script defer src="./app.js"></script>'
    if html.count(old)!=1:raise ValueError("unexpected JavaScript entrypoint")
    html=html.replace(old,'<script defer src="./static-adapter.js"></script>\n  '+old)
    html=html.replace(
       'One direct model API call has been verified; the public-facing replay is explicitly synthetic and does not call Nebius.',
       'One real application API inference was separately verified; this free interactive review is a synthetic replay with no provider key.')
    html=html.replace(
       '<main>',
       '<aside role="note" class="judge-truth-bar"><strong>EVIDENCE TIERS</strong> · '
       'Three historical first-party Playground cases and one direct application-to-Nebius inference were independently source-checked. '
       'The interactive reviewer below uses fictional offline replay and cannot call Nebius or operate real devices. '
       '<a href="./evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json">Read the redacted G1 runtime receipt</a>.'
       '</aside>\n  <main>',1)
    (target/"index.html").write_text(html,encoding="utf-8")
    (target/"evidence").mkdir(exist_ok=True)
    dest_receipt=target/"evidence"/"NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json"
    shutil.copy2(receipt,dest_receipt)
    def dump(name:str,doc:dict):
        if not re.fullmatch(r"[a-zA-Z0-9._-]{3,100}",name):
            raise ValueError("unsafe generated name")
        (data/name).write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
    dump("fixture.json",{"case":fixture(),"provenance":"SYNTHETIC_FIXTURE_ONLY"})
    dump("triage.json",offline_triage(fixture()))
    scenes=handoff_catalogue()
    if len(scenes)!=3:raise ValueError("scene change requires new judge QA")
    dump("handoffs.json",{"scenarios":scenes,"provider_ready":False,
         "source_truth":"ORIGINAL_SYNTHETIC_RUNBOOK_AND_SIGNALS",
         "model":"nvidia/Nemotron-3_5-Lightning","real_calls":0})
    for scene in scenes:
        sid=scene["id"]
        item=offline_handoff(sid)
        if item["provider_api_calls"] or item["provider_verified"]:
            raise ValueError("replay pretends to be live")
        dump("handoff."+sid+".json",item)
        opts=evidence_options(sid)
        dump("options."+sid+".json",opts)
        if len(opts["source_options"])!=3:raise ValueError("counterfactual choices missing")
        for o in opts["source_options"]:
            response=reconcile_evidence(sid,o["id"])
            if (response["provider_api_calls"] or response["provider_verified"]
                 or not response["human_approval_required"]):
                raise ValueError("unsafe counterfeit real inference")
            dump("reconcile."+sid+"."+o["id"]+".json",response)
    adapter=r'''/* Compile-time offline replay, no remote inference, credentials or payment API. */
'use strict';
(()=>{
 const originalFetch=window.fetch.bind(window);
 const scenarios=new Set(['handoff-airflow','handoff-access','handoff-network']);
 const archives={
   'handoff-airflow':new Set(['AIR-JOURNAL-01','AIR-CONFLICT-02','AIR-UNRELATED-03']),
   'handoff-access':new Set(['ACCESS-JOURNAL-01','ACCESS-CONFLICT-02','ACCESS-UNRELATED-03']),
   'handoff-network':new Set(['NETWORK-JOURNAL-01','NETWORK-CONFLICT-02','NETWORK-UNRELATED-03'])
 };
 const err=(status,code)=>new Response(JSON.stringify({error:code}),
   {status,headers:{'Content-Type':'application/json'}});
 const sameKeys=(input,keys)=>{
   if(!input || typeof input!=='object' || Array.isArray(input))return false;
   const actual=Object.keys(input).sort().join(',');
   return actual===keys.slice().sort().join(',');
 };
 async function requestData(filename){
   return originalFetch('./data/'+filename,{cache:'no-store'});
 }
 window.YPAL_JUDGE_SYNTHETIC_REPLAY_ONLY=true;
 window.fetch=async function(resource,params={}){
   const url=typeof resource==='string'?resource:resource?.url;
   if(typeof url!=='string')return err(400,'INVALID_RESOURCE');
   if(!url.startsWith('/api/'))return err(403,'EXTERNAL_FETCH_DISABLED');
   const method=(params.method||'GET').toUpperCase();
   if(method==='GET'){
     if(url==='/api/fixture')return requestData('fixture.json');
     if(url==='/api/handoffs')return requestData('handoffs.json');
     return err(405,'GET_NOT_ALLOWED');
   }
   if(method!=='POST')return err(405,'METHOD_NOT_ALLOWED');
   let input;
   try{input=JSON.parse(params.body)}catch(_){return err(400,'INVALID_JSON')}
   if(url==='/api/handoff'){
     if(!sameKeys(input,['mode','scenario_id'])||input.mode!=='synthetic'
        ||!scenarios.has(input.scenario_id))return err(422,'SYNTHETIC_ONLY');
     return requestData('handoff.'+input.scenario_id+'.json');
   }
   if(url==='/api/evidence-options'){
     if(!sameKeys(input,['scenario_id'])||!scenarios.has(input.scenario_id))
       return err(422,'INVALID_SCENE');
     return requestData('options.'+input.scenario_id+'.json');
   }
   if(url==='/api/reconcile'){
     if(!sameKeys(input,['scenario_id','record_id'])||!scenarios.has(input.scenario_id)
       ||!archives[input.scenario_id].has(input.record_id))return err(422,'INVALID_RECORD');
     return requestData('reconcile.'+input.scenario_id+'.'+input.record_id+'.json');
   }
   if(url==='/api/triage'){
     if(!sameKeys(input,['mode','case'])||input.mode!=='synthetic'||
       input.case?.case_id!=='DEMO-004')return err(422,'SYNTHETIC_ONLY');
     return requestData('triage.json');
   }
   return err(403,'UNRECOGNIZED_API');
 };
})();
'''
    (target/"static-adapter.js").write_text(adapter,encoding="utf-8")
    (target/"README.md").write_text(
        "# Free offline judge replay\n\n"
        "This site is a deterministic original synthetic evaluation interface, not a live model API. "
        "It displays the original five-stage evidence-first handoff and a subsequent "
        "reviewer-driven source reconciliation loop, with three contrasting source options "
        "for each of three fictional incidents, followed by a voluntary, locally hashed "
        "human source-verification decision (not a certified signature). "
        "The same clean-room Python source generates "
        "the static JSON and produces the standalone local application.\n\n"
        "Only a separate redacted local G1 receipt demonstrates a genuine authenticated "
        "Nebius Token Factory request to NVIDIA Nemotron-3_5-Lightning. "
        "The public static site contains no key, paid endpoint or equipment API. "
        "No operational safety efficacy or general model accuracy is claimed.\n",
        encoding="utf-8")
    files=sorted(f for f in target.rglob("*") if f.is_file())
    forbidden=(b"-----BEGIN PRIVATE KEY-----",b"/Volumes/AI-Work/Projects/",
               b"/Users/yangjin/",b"Bearer sk-",b"NEBIUS_API_KEY=")
    for p in files:
        content=p.read_bytes()
        if any(tok in content for tok in forbidden):
            raise ValueError("unsafe public replay content: "+p.name)
    report={
        "status":"PRIVATE_STATIC_CANDIDATE_NOT_DEPLOYED",
        "judge_synthetic_scenarios":3,
        "consequential_source_variants":9,
        "live_provider_calls_from_static_site":0,
        "historical_app_g1_one_call_proof":True,
        "human_approval_required":True,
        "data_origin":"ORIGINAL_SYNTHETIC_ONLY",
        "file_count":len(files),
        "files":[{"name":str(f.relative_to(target)),
                  "sha256":hashlib.sha256(f.read_bytes()).hexdigest()}
                 for f in files],
    }
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",required=True)
    ap.add_argument("--receipt",required=True)
    opts=ap.parse_args()
    result=build(Path(opts.target),Path(opts.receipt))
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
