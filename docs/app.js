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
let archiveChoices=[];
let chosenRecord=null;
let lastReconciled=null;
let latestHumanReceipt=null;
function resetHumanReview(){
  lastReconciled=null;
  latestHumanReceipt=null;
  $('human-review-gate').hidden=true;
  $('human-review-choice').disabled=true;
  $('human-review-choice').replaceChildren(new Option('Select a source-verification action',''));
  $('human-review-record').disabled=true;
  $('human-review-receipt').replaceChildren();
}
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
  $('evidence-lab').hidden=true;
  $('evidence-options').replaceChildren();
  $('evidence-delta').replaceChildren();
  $('evidence-delta').dataset.state='';
  $('evidence-apply').disabled=true;
  archiveChoices=[];
  chosenRecord=null;
  lastHandoffSourceHash=null;
  resetHumanReview();
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
 lastHandoffSourceHash=source.local_source_hash;
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
 // The winning claim is inspectable evidence, not merely an ID string:
 // expose the exact fictional source text and retrieved runbook beside each citation.
 const knownIds=new Set(source.synthetic_signals.map(item=>item.evidence_id));
 if(review.evidence_ids.some(id=>!knownIds.has(id)) ||
    review.runbook_ref!==source.retrieved_runbook?.evidence_id)
   throw Error('Source citations do not match the original packet');
 const ledger=handoffElement('details','source-ledger');
 ledger.append(handoffElement('summary','source-ledger-summary',
     'Inspect cited observations and the original runbook'));
 const rows=handoffElement('div','source-ledger-rows');
 for(const signal of source.synthetic_signals){
   const mark=review.evidence_ids.includes(signal.evidence_id)?'CITED':'UNCITED';
   rows.append(handoffElement('p','source-ledger-row',
       signal.evidence_id+' · '+mark+' · '+signal.text));
 }
 const runbook=source.retrieved_runbook;
 rows.append(handoffElement('p','source-ledger-row',
     runbook.evidence_id+' · '+runbook.title+' · FICTIONAL RUNBOOK'));
 for(const check of runbook.checks){
   rows.append(handoffElement('p','source-ledger-row','CHECK · '+check));
 }
 rows.append(handoffElement('p','source-ledger-hash',
     'Local source SHA-256: '+source.local_source_hash+
     ' · Integrity marker, NOT a sponsor-issued signature.'));
 ledger.append(rows);
 area.append(ledger);
 const t=$('handoff-trace');t.replaceChildren();
 for(const row of result.agent_steps){
   t.append(handoffElement('div','handoff-step',
     row.phase.replaceAll('_',' ')+' · '+row.status));
 }
 text($('handoff-status'),live
   ?'Official Nebius/Nemotron inference returned and passed source checks; no equipment action was taken.'
   :'SYNTHETIC ONLY: runbook and model output are fictional; no Nebius call, real telemetry or machinery action.');
 void loadEvidenceOptions();
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
    :'A previous authenticated application model call passed its source critic; the one-use key was revoked. Offline replay is free. A new privately controlled key would need a separate budget review.');
  $('handoff-run').addEventListener('click',runHandoff);
 }catch(e){text($('handoff-status'),'Local handoff catalogue unavailable. No provider action.');}
}
bootHandoffs();

/* A second, consequential user action. Synthetic archive only: no model or machine API. */
let lastHandoffSourceHash=null;
const EVIDENCE_STATES=new Set([
  'PARTIAL_SOURCE_ADDED_HUMAN_REVIEW',
  'SOURCE_CONFLICT_HUMAN_ESCALATION',
  'UNRELATED_SOURCE_STILL_MISSING'
]);
function proofItem(label,value){
  const node=handoffElement('p','evidence-proof-line');
  node.append(handoffElement('strong','',label+'  '),handoffElement('span','',value));
  return node;
}
async function loadEvidenceOptions(){
  const scene=currentHandoff?.id;
  if(!scene)return;
  const options=$('evidence-options');
  options.replaceChildren();
  $('evidence-lab').hidden=false;
  $('evidence-apply').disabled=true;
  $('evidence-delta').replaceChildren();
  resetHumanReview();
  options.append(handoffElement('p','muted','Opening original fictional source archive…'));
  try{
    const response=await fetch('/api/evidence-options',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({scenario_id:scene})
    });
    const payload=await response.json();
    if(currentHandoff?.id!==scene)return;
    if(!response.ok || payload.mode!=='SYNTHETIC_EVIDENCE_RECONCILIATION_NO_NEBIUS' ||
       payload.archive_truth!=='ORIGINAL_SYNTHETIC_UNATTESTED' ||
       payload.scenario_id!==scene || payload.provider_api_calls!==0 ||
       !Array.isArray(payload.source_options) || payload.source_options.length!==3 ||
       payload.source_options.some(v=>typeof v.id!=='string'||typeof v.title!=='string'||
         typeof v.excerpt!=='string'||typeof v.evidence_id!=='string'))
       throw Error('Source archive is not independently verifiable');
    archiveChoices=payload.source_options;
    options.replaceChildren();
    for(const record of archiveChoices){
      const btn=handoffElement('button','evidence-choice');
      btn.type='button';
      btn.dataset.recordId=record.id;
      btn.setAttribute('aria-pressed','false');
      btn.append(handoffElement('strong','',record.title),
                 handoffElement('small','',record.excerpt));
      btn.addEventListener('click',()=>{
        chosenRecord=record;
        document.querySelectorAll('.evidence-choice').forEach(x=>{
          x.setAttribute('aria-pressed',String(x.dataset.recordId===record.id));
        });
        $('evidence-apply').disabled=false;
        $('evidence-delta').replaceChildren();
        $('evidence-delta').dataset.state='';
        resetHumanReview();
      });
      options.append(btn);
    }
  }catch(_){
    options.replaceChildren(handoffElement('p','muted',
      'Original fictional evidence archive unavailable. No unverified recommendation was produced.'));
  }
}
async function reconcileChosenEvidence(){
  if(!currentHandoff || !chosenRecord)return;
  const scenario=currentHandoff.id;
  const record=chosenRecord.id;
  const button=$('evidence-apply');
  button.disabled=true;
  const output=$('evidence-delta');
  output.dataset.state='';
  resetHumanReview();
  output.replaceChildren(handoffElement('p','muted','Rechecking record linkage and original sources…'));
  try{
    const response=await fetch('/api/reconcile',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({scenario_id:scenario,record_id:record})
    });
    const data=await response.json();
    if(currentHandoff?.id!==scenario || chosenRecord?.id!==record)return;
    const allowed=archiveChoices.find(x=>x.id===record);
    if(!response.ok || !allowed || !data ||
       data.mode!=='SYNTHETIC_EVIDENCE_RECONCILIATION_NO_NEBIUS' ||
       data.scenario_id!==scenario || data.archive_truth!=='ORIGINAL_SYNTHETIC_UNATTESTED' ||
       data.provider_api_calls!==0 || data.provider_verified!==false ||
       data.model_called_for_followup!==false ||
       data.human_approval_required!==true || data.automatic_equipment_actions!==false ||
       data.external_equipment_connections!==0 ||
       data.original_review_kept_intact!==true ||
       data.first_handoff_source_hash!==lastHandoffSourceHash ||
       !data.attached_record || data.attached_record.id!==record ||
       data.attached_record.evidence_id!==allowed.evidence_id ||
       !/^[a-f0-9]{64}$/.test(data.attached_record.archive_sha256) ||
       !data.decision_delta || !EVIDENCE_STATES.has(data.decision_delta.after) ||
       data.decision_delta.before!=='MISSING_OR_UNVERIFIED_RECORD' ||
       data.decision_delta.new_evidence_id!==allowed.evidence_id ||
       !data.decision_delta.comparison_basis ||
       data.decision_delta.comparison_basis.method!=='DETERMINISTIC_SYNTHETIC_ASSET_AND_SIGNAL_CONTRAST' ||
       data.decision_delta.comparison_basis.model_inference!==false ||
       data.decision_delta.automatic_closure!==false ||
       data.decision_delta.safety_action_authorized!==false ||
       !Array.isArray(data.reconciliation_steps) || data.reconciliation_steps.length!==4)
      throw Error('Evidence changed or source proof failed');
    output.replaceChildren();
    const title=handoffElement('strong','evidence-delta-title',
      'EVIDENCE DELTA · '+data.decision_delta.relationship.replaceAll('_',' '));
    const comparison=handoffElement('div','evidence-comparison');
    comparison.append(proofItem('BEFORE',data.decision_delta.before.replaceAll('_',' ')),
                      proofItem('AFTER',data.decision_delta.after.replaceAll('_',' ')));
    const rule=data.decision_delta.comparison_basis;
    output.append(title,comparison,
      proofItem('SOURCE COMPARISON',rule.original_asset+' / '+rule.original_reported_signal+
        ' versus '+rule.followup_asset+' / '+rule.followup_reported_signal),
      proofItem('WHY IT CHANGED',data.decision_delta.explanation),
      proofItem('STILL UNVERIFIED',data.decision_delta.unresolved),
      proofItem('NEXT SOURCE QUESTION',data.decision_delta.next_human_question),
      proofItem('HUMAN-OWNED ACTION',data.decision_delta.next_human_action.replaceAll('_',' ')),
      proofItem('EVIDENCE RECEIPT',
        data.attached_record.evidence_id+' · archive SHA-256 '+data.attached_record.archive_sha256.slice(0,16)+'…'),
      proofItem('BOUNDARY','No automatic closure, equipment action or new Nebius model inference.'));
    output.dataset.state=data.decision_delta.after;
    activateHumanDecision(data);
  }catch(_){
    output.replaceChildren(handoffElement('p','muted',
      'Evidence reconciliation refused. No new decision or equipment action was taken.'));
  }finally{
    if(currentHandoff?.id===scenario && chosenRecord?.id===record)button.disabled=false;
  }
}
$('evidence-apply').addEventListener('click',reconcileChosenEvidence);

/* No authority delegation: an actual human click records a fictional audit choice
 * in volatile browser memory. Hash is a local integrity checksum, NOT signature. */
const HUMAN_CHOICES={
  'PARTIAL_SOURCE_ADDED_HUMAN_REVIEW':[
    ['HOLD_FOR_SOURCE_CHECK','Hold: request the original signed source record'],
    ['REQUEST_ORIGINAL_RECORD','Request signed source record from qualified reviewer']
  ],
  'SOURCE_CONFLICT_HUMAN_ESCALATION':[
    ['HOLD_FOR_SOURCE_CHECK','Hold: verify both contradictory source records'],
    ['ESCALATE_SOURCE_CONFLICT','Escalate contradiction to qualified supervisor']
  ],
  'UNRELATED_SOURCE_STILL_MISSING':[
    ['HOLD_FOR_SOURCE_CHECK','Hold: original relevant record still missing'],
    ['REJECT_UNRELATED_SOURCE','Reject unrelated record; request a matching source']
  ]
};
function activateHumanDecision(data){
  if(!data?.decision_delta || !HUMAN_CHOICES[data.decision_delta.after])return;
  if(data.scenario_id!==currentHandoff?.id || data.attached_record?.id!==chosenRecord?.id)
    return;
  lastReconciled=data;
  latestHumanReceipt=null;
  const options=$('human-review-choice');
  options.replaceChildren(new Option('Select a source-verification action',''));
  for(const [value,label] of HUMAN_CHOICES[data.decision_delta.after]){
    options.append(new Option(label,value));
  }
  options.value='';
  options.disabled=false;
  $('human-review-record').disabled=true;
  $('human-review-receipt').replaceChildren();
  $('human-review-gate').hidden=false;
}
$('human-review-choice').addEventListener('change',()=>{
  $('human-review-record').disabled=!lastReconciled ||
    !HUMAN_CHOICES[lastReconciled.decision_delta.after]?.some(
      ([value])=>value===$('human-review-choice').value);
});
async function recordHumanReview(){
  const data=lastReconciled;
  const choice=$('human-review-choice').value;
  if(!data || data.scenario_id!==currentHandoff?.id ||
     data.attached_record?.id!==chosenRecord?.id ||
     !HUMAN_CHOICES[data.decision_delta.after].some(([v])=>v===choice))return;
  if(!window.crypto?.subtle) {
    $('human-review-receipt').replaceChildren(
      handoffElement('p','muted','Local SHA-256 unavailable. No audit receipt recorded.'));
    return;
  }
  const receipt={
    kind:'UNAUTHENTICATED_FICTIONAL_HUMAN_HANDOFF_DECISION',
    case_id:data.scenario_id,
    added_record_id:data.attached_record.id,
    added_source_sha256:data.attached_record.archive_sha256,
    original_source_sha256:data.first_handoff_source_hash,
    derived_evidence_state:data.decision_delta.after,
    permitted_human_choice:choice,
    selected_at_browser_utc:new Date().toISOString(),
    no_equipment_actions:true,
    incident_not_closed:true,
    does_not_verify_staff_identity:true,
    not_a_vendor_or_legal_signature:true
  };
  const encoded=new TextEncoder().encode(JSON.stringify(receipt));
  const digest=await crypto.subtle.digest('SHA-256',encoded);
  if(lastReconciled!==data || currentHandoff?.id!==receipt.case_id ||
     chosenRecord?.id!==receipt.added_record_id)return;
  const sha=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
  latestHumanReceipt={...receipt,local_receipt_sha256:sha};
  const output=$('human-review-receipt');
  output.replaceChildren(
    proofItem('RECORDED HUMAN CHOICE',choice.replaceAll('_',' ')),
    proofItem('LOCAL RECEIPT HASH',sha),
    proofItem('AUDIT LIMIT',
      'An in-browser choice on fictional data; not an authenticated signature, incident closure or equipment permission.'));
  $('human-review-choice').disabled=true;
  $('human-review-record').disabled=true;
}
$('human-review-record').addEventListener('click',recordHumanReview);
