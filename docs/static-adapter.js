/* Compile-time offline replay, no remote inference, credentials or payment API. */
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
