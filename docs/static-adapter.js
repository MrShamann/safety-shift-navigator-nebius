/* Static, deterministic, original synthetic demo adapter.
 * Never sends model requests; never accepts a client API key.
 * The actual Python application made one separately verified Nebius Token Factory
 * call, documented in evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json.
 */
'use strict';
(()=>{
 const realFetch=window.fetch.bind(window);
 const sceneIds=new Set(['handoff-airflow','handoff-access','handoff-network']);
 const error=(status,msg)=>new Response(JSON.stringify({error:msg}),{
   status,headers:{'Content-Type':'application/json'}
 });
 window.fetch=async function resourceOnly(input,opts={}){
   const u=typeof input==='string'?input:input?.url;
   if(typeof u!=='string')return error(400,'INVALID_REQUEST');
   const method=(opts.method||'GET').toUpperCase();
   if(u==='/api/fixture' && method==='GET')
     return realFetch('./data/fixture.json',{cache:'no-store'});
   if(u==='/api/handoffs' && method==='GET')
     return realFetch('./data/handoffs.json',{cache:'no-store'});
   if(u==='/api/handoff' && method==='POST'){
     let data;
     try{data=JSON.parse(opts.body)}catch(_){return error(400,'INVALID_JSON')}
     if(!data || data.mode!=='synthetic'||!sceneIds.has(data.scenario_id)||
       Object.keys(data).sort().join(',')!=='mode,scenario_id')
       return error(422,'STATIC_DEMO_NO_PROVIDER_CALLS');
     return realFetch('./data/'+data.scenario_id+'.json',{cache:'no-store'});
   }
   if(u==='/api/triage' && method==='POST'){
     let data;
     try{data=JSON.parse(opts.body)}catch(_){return error(400,'INVALID_JSON')}
     if(!data || data.mode!=='synthetic'||data.case?.case_id!=='DEMO-004')
       return error(422,'STATIC_DEMO_NO_PROVIDER_CALLS');
     return realFetch('./data/triage.json',{cache:'no-store'});
   }
   return error(403,'EXTERNAL_RESOURCE_BLOCKED');
 };
 window.YPAL_STATIC_DEMO=true;
})();
