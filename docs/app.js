'use strict';
const $ = id => document.getElementById(id);
let syntheticCase = null;
function text(node, value){node.textContent = String(value);}
async function loadCase(){
  try{
    const reply = await fetch('/api/fixture',{cache:'no-store'});
    if(!reply.ok) throw Error('Fixture failed');
    const data = await reply.json();
    syntheticCase = data.case;
    const area = $('signals');
    area.replaceChildren();
    for(const row of syntheticCase.signals){
      const item=document.createElement('div');
      item.className='signal';
      const identifier=document.createElement('b');
      const description=document.createElement('p');
      text(identifier,row.id);
      text(description,row.observation);
      item.append(identifier,description);
      area.append(item);
    }
    text($('status'),'Fixture verified: '+syntheticCase.case_id);
  }catch(e){text($('status'),'Synthetic fixture could not be loaded.');}
}
$('run').addEventListener('click',async()=>{
  if(!syntheticCase)return;
  $('run').disabled=true;
  text($('status'),'Running bounded analysis…');
  try{
    const isLive=$('real').checked;
    const request={mode:isLive?'provider':'synthetic',case:syntheticCase};
    const r=await fetch('/api/triage',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
    const data=await r.json();
    if(!r.ok)throw Error(data.error||'BLOCKED');
    text($('mode'),data.mode);
    text($('severity'),data.output.severity);
    text($('action'),data.output.next_action.replaceAll('_',' '));
    text($('reason'),data.output.reason);
    text($('ids'),data.output.evidence_ids.join(', '));
    text($('status'),data.provider_verified?'Verified real Nebius API call — human review only.':'Offline synthetic mock. No Nebius API call was made.');
  }catch(e){text($('status'),'Blocked: '+e.message+'. No equipment action was taken.');}
  finally{$('run').disabled=false;}
});
loadCase();

let handoffScenes=[];
let currentHandoff=null;
function chooseHandoff(id){
  const source=handoffScenes.find(s=>s.id===id);
  if(!source)return;
  currentHandoff=source;
  document.querySelectorAll('.handoff-choice').forEach(b=>{
    b.setAttribute('aria-pressed',String(b.dataset.id===id));
  });
  text($('handoff-title'),source.title);
  $('handoff-review').replaceChildren(Object.assign(
      document.createElement('p'),{textContent:source.mission,className:'muted'}));
  $('handoff-trace').replaceChildren();
  text($('handoff-source'),'NOT RUN');
}
function handoffElement(tag,cls,value){
 const el=document.createElement(tag);
 if(cls)el.className=cls;
 if(value!==undefined)el.textContent=String(value);
 return el;
}
function showHandoff(result){
 if(!result || result.source_truth!=='ORIGINAL_SYNTHETIC_RUNBOOK_AND_SIGNALS'
   || result.human_approval_required!==true
   || result.automatic_equipment_actions!==false
   || result.external_equipment_connections!==0)throw Error('Untrusted handoff contract');
 const fake=result.mode==='SYNTHETIC_MULTI_TOOL_REPLAY_NO_NEBIUS' &&
            result.provider_verified===false && result.provider_api_calls===0;
 const live=result.mode==='NEBIUS_NEMOTRON_ONE_CALL_SOURCE_CHECKED' &&
            result.provider_verified===true && result.provider_api_calls===1 &&
            result.provider_model==='nvidia/Nemotron-3_5-Lightning';
 if(!fake&&!live)throw Error('Provider origin was not established');
 const source=result.source_packet;
 if(!source || source.all_sources_are_synthetic!==true ||
    !Array.isArray(source.synthetic_signals) ||
    typeof source.local_source_hash!=='string' ||
    source.local_source_hash.length!==64)throw Error('Source evidence missing');
 const review=result.review;
 if(!review || !Array.isArray(review.evidence_ids) ||
    !review.evidence_ids.length || !Array.isArray(result.agent_steps) ||
    result.agent_steps.length!==5)throw Error('Incomplete agent evidence');
 text($('handoff-title'),currentHandoff.title);
 text($('handoff-source'),live?'NEMOTRON API / VERIFIED':'SYNTHETIC REPLAY / NO NEBIUS');
 const area=$('handoff-review');area.replaceChildren();
 const header=handoffElement('div','handoff-summary');
 header.append(handoffElement('span','handoff-severity',review.severity.toUpperCase()),
   handoffElement('strong','',review.next_action.replaceAll('_',' ').toUpperCase()));
 area.append(header);
 area.append(handoffElement('p','handoff-why',review.reason));
 const audit=handoffElement('div','handoff-audit');
 audit.append(
   handoffElement('small','', 'Cited source IDs: '+review.evidence_ids.join(', ')),
   handoffElement('small','', 'Original runbook: '+review.runbook_ref),
   handoffElement('small','', 'Unresolved: '+review.missing_evidence),
   handoffElement('small','', 'Human verification: '+review.question_for_human)
 );
 area.append(audit);
 const t=$('handoff-trace');t.replaceChildren();
 for(const row of result.agent_steps){
   t.append(handoffElement('div','handoff-step',
     row.phase.replaceAll('_',' ')+' · '+row.status));
 }
 text($('handoff-status'),live
   ?'Official Nebius/Nemotron inference returned and passed source checks; no equipment action was taken.'
   :'SYNTHETIC ONLY: runbook and model output are fictional; no Nebius call, real telemetry or machinery action.');
}
async function runHandoff(){
 if(!currentHandoff)return;
 const btn=$('handoff-run');btn.disabled=true;
 const live=$('handoff-live').checked;
 text($('handoff-status'),live
   ?'Checking licensed credits and guarded Nemotron request…'
   :'Retrieving fictional runbook and executing five-stage offline replay…');
 try{
  const r=await fetch('/api/handoff',{method:'POST',
     headers:{'Content-Type':'application/json'},
     body:JSON.stringify({scenario_id:currentHandoff.id,
                         mode:live?'provider':'synthetic'})});
  const value=await r.json();
  if(!r.ok)throw Error(value.error||'Unverified source');
  showHandoff(value);
 }catch(e){
  text($('handoff-source'),'REJECTED');
  text($('handoff-title'),'No verified recommendation.');
  $('handoff-review').replaceChildren(handoffElement('p','muted',
    'Agent abstained because the scenario, model quota or evidence contract could not be validated.'));
  $('handoff-trace').replaceChildren();
  text($('handoff-status'),'BLOCKED — '+e.message+
      ' · No external equipment control or silent model fallback.');
 }finally{btn.disabled=false;}
}
async function bootHandoffs(){
 try{
  const response=await fetch('/api/handoffs',{cache:'no-store'});
  if(!response.ok)throw Error('No original handoff catalogue');
  const payload=await response.json();
  if(payload.source_truth!=='ORIGINAL_SYNTHETIC_RUNBOOK_AND_SIGNALS' ||
     !Array.isArray(payload.scenarios)||payload.scenarios.length!==3)
     throw Error('Invalid handoff catalogue');
  handoffScenes=payload.scenarios;
  const holder=$('handoff-scenarios');holder.replaceChildren();
  for(const scene of handoffScenes){
   const btn=handoffElement('button','handoff-choice');
   btn.type='button';btn.dataset.id=scene.id;
   btn.setAttribute('aria-pressed','false');
   btn.append(handoffElement('strong','',scene.title),
      handoffElement('small','',scene.mission));
   btn.addEventListener('click',()=>chooseHandoff(scene.id));
   holder.append(btn);
  }
  chooseHandoff(handoffScenes[0].id);
  $('handoff-run').disabled=false;
  $('handoff-live').disabled=payload.provider_ready!==true;
  text($('handoff-gate'),payload.provider_ready
    ?'Configured event key and verified zero-spend model gate. Each approved call is one Nemotron completion.'
    :'Token Factory promotional credit is verified, but this application remains locked until a scoped key and zero-overage authorization are available.');
  $('handoff-run').addEventListener('click',runHandoff);
 }catch(e){text($('handoff-status'),'Local handoff catalogue unavailable. No provider action.');}
}
bootHandoffs();
