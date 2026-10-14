// Separate AI estimates and human judgments; polling never discards a typed draft.
const reviewEndpoint='__REVIEW_URL__';
const reviewStyle=document.createElement('style');reviewStyle.textContent=`
.review-box{background:#243328;padding:14px;border:1px solid #526c57;border-radius:8px;margin-top:12px}.ai-score{font-weight:700;font-size:19px}.ai-detail,.saved,.message,.history{font-size:14px;margin-top:7px;white-space:pre-wrap;overflow-wrap:anywhere}.ai-reason{margin:7px 0;font-size:14px}.rating-form{border-top:1px solid #526c57;padding-top:12px;margin-top:12px}.rating-form label{display:block;margin-bottom:10px}.rating-form select{margin-left:8px}.rating-form textarea{display:block;width:100%;min-height:85px;margin-top:7px;resize:vertical;font:inherit;padding:9px;border-radius:5px}.saved{color:#dcf1d6}.message{color:#f1d997}.rating-form button{background:#d4ebc4;font-weight:700}button:disabled{opacity:.55;cursor:default}.hint{font-size:13px;color:#bed0c1}details{font-size:13px;margin-top:8px}summary{cursor:pointer}#editing{color:#f1d997;font-size:13px}[hidden]{display:none!important}@media(max-width:650px){.row{grid-template-columns:repeat(2,minmax(0,1fr))}.row>.cell:last-child{grid-column:1/-1}.row>.cell:last-child img,.row>.cell:last-child .pending{height:350px}.labels span:last-child{display:none}.labels{grid-template-columns:1fr 1fr}}`;
document.head.append(reviewStyle);
const flowStyle=document.createElement('style');flowStyle.textContent=`.labels,.row{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.cell img,.pending{height:340px}.baseline-link{display:block;margin-top:8px;font-size:14px}@media(max-width:850px){.cell img,.pending{height:260px}.labels,.row{gap:8px}}@media(max-width:650px){.row{grid-template-columns:repeat(2,minmax(0,1fr))}.row>.cell:last-child{grid-column:auto}.row>.cell:last-child img,.row>.cell:last-child .pending{height:260px}.labels{display:none}.cell:before{display:block;content:attr(data-stage);font-weight:700;margin-bottom:8px}.review-box{padding:10px}}@media(max-width:420px){.row{grid-template-columns:1fr}.cell img,.pending,.row>.cell:last-child img,.row>.cell:last-child .pending{height:320px}}`;
document.head.append(flowStyle);
const starStyle=document.createElement('style');starStyle.textContent=`.rating-form{border:0;padding:0;margin:0}.stars{display:flex;gap:1px;flex-wrap:nowrap}.star-field{border:0;padding:0;margin:0 0 10px;min-width:0}.star-field legend{font-size:19px;font-weight:700;margin-bottom:7px}.rating-form .star-choice{display:block;position:relative;margin:0;cursor:pointer;line-height:1}.star-choice input{position:absolute;opacity:0;width:1px;height:1px;padding:0}.star-choice span{display:block;font-size:clamp(17px,1.65vw,29px);padding:3px 1px;color:#ffdb75}.star-choice input:focus-visible+span{outline:2px solid #fff;border-radius:3px}.star-choice input:disabled+span{opacity:.4;cursor:default}.human-rating-value{font-size:14px;margin-top:5px;color:#ffdb75}.ai-summary{border-top:1px solid #526c57;padding-top:12px;margin-top:12px}.rating-form textarea{background:#fff;color:#172a1c}.rating-form>button{width:100%;padding:11px;font-size:17px}@media(max-width:650px){.star-choice span{font-size:22px}}@media(max-width:420px){.star-choice span{font-size:26px}}`;
document.head.append(starStyle);
const auditStyle=document.createElement('style');auditStyle.textContent='.ai-dimensions{font-size:15px;font-weight:700;margin:8px 0}.ai-findings{font-size:14px;white-space:pre-wrap;overflow-wrap:anywhere}.ai-verdict{color:#f1d997;font-size:15px;margin:6px 0}';document.head.append(auditStyle);
document.querySelector('.labels').innerHTML='<span>Dog Input</span><span>Final Dog</span><span>Reference Costume</span><span>Output + scores</span>';
document.querySelector('header > p').textContent='Dog Input → Final Dog → Reference Costume → Output. Live demonstration on your 96 GB GPU.';
document.querySelector('header').insertAdjacentHTML('beforeend','<p id="review-summary"></p><p class="hint">AI scores are estimates. Your independent score and notes help compare workflow revisions. Submitting feedback does not automatically train the model.</p>');
document.querySelector('#review-summary').insertAdjacentHTML('beforebegin','<section id="judge-panel" class="stat" aria-label="Live AI reviewer"><strong id="judge-activity">Connecting to AI reviewer…</strong><p id="judge-queue"></p><p id="judge-speed"></p><button id="show-judge">Show image being scored</button></section>');
$('#mode').insertAdjacentHTML('beforeend','<option value="ai-scoring">AI scoring now</option>');
$('#mode').insertAdjacentHTML('beforeend','<option value="auto-refine">Auto refinement</option>');
$('#judge-panel').insertAdjacentHTML('afterend','<section class="stat" id="auto-panel" hidden><strong>Automatic workflow refinement</strong><p id="auto-status"></p></section>');
document.querySelector('nav').insertAdjacentHTML('beforebegin','<section id="input-catalog" hidden><details><summary id="input-catalog-summary">Submitted dog inputs</summary><p>Clear inputs drive tuning. Difficult photos remain visible for broader testing. Click a photo to inspect the native-pixel crop.</p><div id="input-dogs"></div></details></section>');
const inputStyle=document.createElement('style');inputStyle.textContent='#input-catalog{padding:16px 4%;background:#203127}#input-catalog summary{font-size:20px;font-weight:700}#input-dogs{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-top:16px}.input-dog{padding:12px;background:#14221a;border-radius:8px}.input-dog img{width:100%;height:210px;object-fit:contain}.input-dog .input-face{height:100px;margin-top:6px}.input-dog p{font-size:14px}.input-quality{color:#f1d997;font-size:14px;margin-top:8px}';document.head.append(inputStyle);
$('#show-judge').onclick=()=>{$('#pack').value='all';$('#mode').value='ai-scoring';$('#search').value='';page=0;draw()};
document.querySelector('nav').insertAdjacentHTML('beforeend','<span id="editing"></span>');
$('#mode').insertAdjacentHTML('beforeend','<option value="unreviewed">Needs your review</option><option value="reviewed">Reviewed</option><option value="fur-body">AI flagged fur / body</option><option value="body-repairs">Body repairs</option>');
const originalFiltered=filtered;
filtered=function(){let rows=originalFiltered();if($('#mode').value==='unreviewed')rows=rows.filter(r=>r.output&&!r.human_review);if($('#mode').value==='reviewed')rows=rows.filter(r=>r.human_review);if($('#mode').value==='fur-body')rows=rows.filter(r=>r.ai_review&&(r.ai_review.fur<=5||r.ai_review.body<=5||(r.ai_review.defects||[]).some(d=>['fur','body'].includes(d.area)&&d.severity==='major')));if($('#mode').value==='body-repairs')rows=rows.filter(r=>r.repair_version);if($('#mode').value==='auto-refine')rows=rows.filter(r=>r.auto_refine_version);if($('#mode').value==='ai-scoring')rows=rows.filter(r=>r.id===state.judge?.active_row_id);return rows};
function draftKey(r){return 'fpg-review:'+r.id+':'+r.output_sha256}
function getDraft(r){try{return JSON.parse(localStorage.getItem(draftKey(r))||'null')}catch{return null}}
function rememberDraft(r,value){try{value?localStorage.setItem(draftKey(r),JSON.stringify(value)):localStorage.removeItem(draftKey(r))}catch{}}
function makeReview(card,r){
card.dataset.rowId=r.id;
const prepared=document.createElement('div');prepared.className='cell prepared-cell';
prepared.innerHTML=r.prepared?`<a href="${media(r.prepared)}" target="_blank" rel="noopener"><img loading="lazy" src="${media(r.prepared)}" alt="Final Dog: prepared version of the original dog"></a><div class="caption">${esc(r.preparation||'Prepared dog reference')}</div>`:'<div class="pending">Original photo used in this baseline</div><div class="caption">No preparation step in this earlier workflow.</div>';
card.insertBefore(prepared,card.children[1]);
['Dog Input','Final Dog','Reference Costume','Output + scores'].forEach((stage,index)=>card.children[index].dataset.stage=stage);
if(r.input_quality)card.children[0].insertAdjacentHTML('beforeend',`<div class="input-quality">${esc(r.input_quality==='clear'?'Clear input':'Difficult input')}: ${esc(r.input_quality_notes||'')}</div>`);
card.querySelector('.cell:last-child').insertAdjacentHTML('beforeend',`<div class="review-box"><form class="rating-form"><input type="hidden" class="human-score"><fieldset class="star-field"><legend>Your rating</legend><div class="stars">${Array.from({length:10},(_,i)=>`<label class="star-choice" title="${i+1} out of 10"><input type="radio" name="rating" value="${i+1}" required aria-label="${i+1} out of 10 stars"><span aria-hidden="true">☆</span></label>`).join('')}</div><div class="human-rating-value">Click a star: 1–10</div></fieldset><label>Your notes<textarea class="notes" maxlength="2000" placeholder="What looks wrong or right? Face, eyes, ears, markings, pose…"></textarea></label><button type="submit">Submit review</button><div class="message" role="status" aria-live="polite"></div></form><div class="saved"></div><details class="human-history" hidden><summary>Previous submitted reviews</summary><div class="history"></div></details><div class="ai-summary"><div class="ai-score"></div><p class="ai-reason"></p><details class="ai-more" hidden><summary>AI assessment details</summary><div class="ai-detail"></div></details></div><div class="workflow caption"></div></div>`);
const form=card.querySelector('form'),score=card.querySelector('.human-score'),notes=card.querySelector('.notes');
if(r.auto_refine_version)card.querySelector('.star-field legend').textContent='Your rating (optional)';
if(r.auto_refine_version)card.querySelector('.review-box').insertAdjacentHTML('afterbegin','<details class="auto-explanation"><summary>What the AI changed for this attempt</summary><div class="auto-changes ai-detail"></div></details>');
card.querySelector('.review-box').insertAdjacentHTML('afterbegin','<div class="ai-overview ai-dimensions"></div>');
if(r.baseline_output)card.querySelector('.workflow').insertAdjacentHTML('afterend',`<a class="baseline-link" href="${media(r.baseline_output)}" target="_blank" rel="noopener">${esc(r.baseline_label||'Compare earlier output without dog preparation')}</a>`);
if(r.repair_version||r.auto_refine_version)card.querySelector('.workflow').insertAdjacentHTML('afterend','<details class="repair-evidence"><summary>Before repair and repair area</summary><div class="repair-assets"></div></details>');
form.addEventListener('input',event=>{if(event.target.type==='radio')score.value=event.target.value;paintStars(card,score.value);rememberDraft(card.current,{score:score.value,notes:notes.value});card.dirty=true;card.querySelector('.message').textContent='Draft saved in this browser. Click Submit review to send it.'});
form.addEventListener('submit',async event=>{
event.preventDefault();const current=card.current;if(!current.output_sha256)return;
const button=form.querySelector('button');button.disabled=true;card.saving=true;
let saved=getDraft(current)||{},submission=saved.submission_id||crypto.randomUUID();rememberDraft(current,{score:score.value,notes:notes.value,submission_id:submission});
try{const response=await fetch(reviewEndpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({row_id:current.id,output_sha256:current.output_sha256,score:Number(score.value),notes:notes.value,submission_id:submission})});const data=await response.json();if(!response.ok)throw Error(data.error||'Could not save');current.human_review=data.review;current.human_reviews=[...(current.human_reviews||[]).filter(x=>x.id!==data.review.id),data.review];rememberDraft(current,null);card.dirty=false;card.querySelector('.message').textContent='Saved. Your score and notes are attached to this output.';paintReview(card,current)}catch(error){card.querySelector('.message').textContent=error.message+' Your draft is kept; please retry.'}finally{card.saving=false;button.disabled=false}
});
}
function paintStars(card,value){for(const radio of card.querySelectorAll('.stars input')){radio.checked=Number(radio.value)===Number(value);radio.nextElementSibling.textContent=Number(radio.value)<=Number(value)?'★':'☆'}card.querySelector('.human-rating-value').textContent=value?`${value} / 10 stars`:'Click a star: 1–10'}
function paintReview(card,r){
let ai=r.ai_review;
const repairAssets=card.querySelector('.repair-assets');
if(repairAssets&&repairAssets.dataset.mask!==String(r.repair_mask||'')){repairAssets.dataset.mask=String(r.repair_mask||'');repairAssets.innerHTML=`<a href="${media(r.baseline_output)}" target="_blank" rel="noopener"><img loading="lazy" src="${media(r.baseline_output)}" alt="Original result before body repair"></a><p>Original result before body repair</p>${r.repair_mask?`<a class="baseline-link" href="${media(r.repair_mask)}" target="_blank" rel="noopener">View the whole-body repair mask</a><a class="baseline-link" href="${media(r.repair_design)}" target="_blank" rel="noopener">View costume reference with old animal fur removed</a>`:'<p>Locating the animal and costume…</p>'}`;}
const wholePet=ai&&Number.isInteger(ai.fur)&&Number.isInteger(ai.body);
card.querySelector('.ai-overview').textContent=(ai?`AI ${ai.score}/10${wholePet?` · Face ${ai.identity} · Fur ${ai.fur} · Body ${ai.body}`:''}`:r.ai_status==='Scoring'?'AI is checking face, fur and body…':r.output?'AI score queued':'AI waiting for image')+(ai&&r.ai_status==='Scoring'?' · Rechecking now…':r.ai_status==='Needs attention'?' · Review needs attention':'');
if(!card.querySelector('.ai-summary .ai-dimensions'))card.querySelector('.ai-score').insertAdjacentHTML('afterend','<div class="ai-dimensions"></div><div class="ai-verdict"></div><div class="ai-findings"></div>');
card.querySelector('.ai-score').textContent=ai?`${wholePet?'Whole-pet AI score':'Earlier AI score'}: ${ai.score} / 10`:r.ai_status==='Scoring'?'AI assessment in progress…':r.output?'AI score: waiting for assessment':'AI score: waiting for output';
card.querySelector('.ai-summary .ai-dimensions').textContent=wholePet?`Face ${ai.identity}/10 · Fur ${ai.fur}/10 · Body ${ai.body}/10 · Design ${ai.template}/10`:ai?'Fur/body re-review pending.':'';
const priorAi=(r.ai_previous||[]).filter(a=>a.rubric==='pet-identity-v2-qwen32b').at(-1);
const target=r.auto_target||10;
const limits=r.output_thresholds||{identity:target,fur:target,body:target,template:target};
const autoTarget=wholePet&&Object.keys(limits).every(k=>ai[k]>=limits[k])&&!(ai.defects||[]).some(d=>d.severity==='major')&&ai.confidence==='high'&&(!r.output_thresholds||r.input_photo_score>=7);
const limitLabel=r.output_thresholds?'Input 7+; face 9, fur 9, body 7, design 9':`${target}/10 in every dimension`;
card.querySelector('.ai-verdict').textContent=wholePet?(r.auto_refine_version?(autoTarget?'AI target met on this image; cross-dog checks still apply':`Below target: ${limitLabel}`)+(r.output_thresholds?'':' · Earlier acceptance rule'):(ai.verdict||'Human review required'))+(priorAi?` · Earlier AI score ${priorAi.score}/10`:''):'';
const changes=card.querySelector('.auto-changes');if(changes)changes.textContent=[r.auto_rationale,...(r.auto_corrections||[]),...(r.auto_changes||[]).map(c=>`${c.parameter}: ${c.before??'initial'} → ${c.after}`)].filter(Boolean).join('\n')||'Earlier policy: workflow settings selected from the lowest scoring dimensions.';
card.querySelector('.ai-findings').textContent=wholePet?(ai.defects||[]).slice(0,3).map(d=>`${d.area.toUpperCase()}: ${d.evidence}\nSuggested fix: ${d.correction}`).join('\n\n'):'';
card.querySelector('.ai-reason').textContent=ai?ai.reason||'':r.ai_status==='Needs attention'?'Assessment needs attention; your review is still available.':'';
card.querySelector('.ai-more').hidden=!ai;
if(ai)card.querySelector('.ai-summary .ai-detail').textContent=wholePet?`Face: ${ai.face_notes}\nFur: ${ai.fur_notes}\nBody: ${ai.body_notes}\nPreparation: ${ai.preparation_notes}\n\n${(ai.defects||[]).map(d=>`${d.severity} ${d.area}: ${d.evidence}\nSuggested fix: ${d.correction}`).join('\n\n')}\n${ai.model} · ${ai.rubric}\nAI estimate; compare it with your own judgment.`:`Likeness ${ai.identity}/10 · Template ${ai.template}/10 · Anatomy ${ai.anatomy}/10\n${(ai.flags||[]).join('; ')}\n${ai.model} · ${ai.rubric}\nEarlier scoring method; fur/body re-review pending.`;
const form=card.querySelector('form');for(const control of form.elements)control.disabled=!r.output_sha256||card.saving;
const previous=r.human_review;card.querySelector('.saved').textContent=previous?`Last submitted score: ${previous.score} / 10 · ${new Date(previous.created_at*1000).toLocaleString()}\n${previous.notes}`:'No human review submitted yet.';
const history=r.human_reviews||[];card.querySelector('.human-history').hidden=history.length<2;card.querySelector('.history').textContent=history.slice(0,-1).reverse().map(h=>`${h.score}/10 · ${new Date(h.created_at*1000).toLocaleString()}\n${h.notes}`).join('\n\n');
card.querySelector('.workflow').textContent=r.workflow_id?'Workflow: '+r.workflow_id:'';
if(!card.dirty&&!card.saving&&!form.contains(document.activeElement)){const saved=getDraft(r);card.querySelector('.human-score').value=saved?.score??previous?.score??'';card.querySelector('.notes').value=saved?.notes??previous?.notes??'';paintStars(card,card.querySelector('.human-score').value);if(saved)card.querySelector('.message').textContent='Unsaved draft restored. Click Submit review to send it.'}
}
const originalDraw=draw;
let lastInputCatalog='';
draw=function(){
const catalog=state.input_catalog||{},inputDogs=catalog.dogs||[];$('#input-catalog').hidden=!inputDogs.length;
$('#input-catalog-summary').textContent=`Submitted dog inputs: ${catalog.total||0} · ${catalog.clear||0} clear · ${catalog.challenging||0} difficult`;
const catalogKey=JSON.stringify(catalog);if(catalogKey!==lastInputCatalog){lastInputCatalog=catalogKey;$('#input-dogs').innerHTML=inputDogs.map(d=>`<article class="input-dog"><strong>${esc(d.label)}</strong><a href="${media(d.input)}" target="_blank" rel="noopener"><img loading="lazy" src="${media(d.thumbnail||d.input)}" alt="${esc(d.label)}"></a><a href="${media(d.crop)}" target="_blank" rel="noopener"><img class="input-face" loading="lazy" src="${media(d.crop_thumbnail||d.crop)}" alt="Identity face crop"></a><p>${esc(d.quality_tier==='clear'?'Clear input':'Difficult input')} · ${esc(d.quality_notes)}</p></article>`).join('')}
let assessed=state.rows.filter(r=>r.ai_review),reviewed=state.rows.filter(r=>r.human_review);
const audited=assessed.filter(r=>Number.isInteger(r.ai_review.fur)&&Number.isInteger(r.ai_review.body));
$('#review-summary').textContent=`Whole-pet AI audits ${audited.length} · Earlier AI reviews ${assessed.length-audited.length} · Human reviewed ${reviewed.length}`;
const judge=state.judge||{};
$('#judge-activity').textContent=judge.status==='Scoring'?`AI is scoring: ${judge.active_label} · ${judge.elapsed_seconds}s`:judge.status==='Waiting'?'AI reviewer: caught up and waiting for the next image':`AI reviewer: ${judge.status||'Connecting…'}`;
$('#judge-queue').textContent=judge.completed_images==null?'':`${judge.scored} / ${judge.completed_images} images scored · ${judge.unscored} awaiting first score · ${judge.reaudit_pending} older scores awaiting whole-pet recheck`;
$('#judge-speed').textContent=judge.recent_score_seconds?`Recent scoring: ${judge.recent_score_seconds}s/image (${judge.timing_samples} samples) · Recent generation: ${judge.recent_render_seconds??'—'}s/image · Qwen3-VL-32B`:'Measuring compact review speed · Qwen3-VL-32B';
$('#show-judge').disabled=judge.status!=='Scoring'||!judge.active_row_id;
const auto=state.auto_refine||{};$('#auto-panel').hidden=!auto.run;
const autoRender=state.rows.find(r=>r.auto_refine_version===auto.run&&r.status==='Rendering');
const autoPhase=autoRender?`Rendering ${autoRender.auto_stage} · recipe ${autoRender.auto_attempt} · ${autoRender.label}`:auto.phase||'';
$('#auto-status').textContent=auto.run?`${auto.status} · ${auto.current_template||'Preparing'} · ${autoPhase} · ${auto.target||''} · ${auto.generations}/${auto.max_generations} attempts · ${auto.finished}/${auto.templates} workflows evaluated · ${auto.passed} met all AI targets. No rating submission needed. View: Auto refinement.`:'';
if(state.batch?.status==='Paused'){$('#eta').textContent='Paused';$('#notice').textContent='Prior batch paused.'}
if((document.activeElement?.closest('.rating-form')&&document.activeElement.matches('textarea,input[type=radio]'))||[...cards.values()].some(c=>c.saving)){$('#editing').textContent='Live reordering paused while you write.';return}
$('#editing').textContent='';originalDraw();
for(const [id,card] of cards){const r=state.rows.find(r=>r.id===id);if(!r)continue;if(!card.querySelector('.review-box'))makeReview(card,r);card.current=r;paintReview(card,r)}
};

// Stable cards retain review drafts and horizontal position while scores arrive.
$('#mode').insertAdjacentHTML('beforeend','<option value="generations">Generations side by side</option>');
document.querySelector('.labels').insertAdjacentHTML('beforebegin',`<section id="generation-view" hidden>
<h2>Generation history</h2><p>Choose a workflow. Each dog appears below the previous one; slide across its row to compare generations, AI feedback and your reviews.</p>
<label>Costume workflow <select id="generation-group" aria-label="Costume workflow"></select></label>
<p id="generation-count"></p><div id="generation-dogs"></div></section>`);
$('#auto-panel').insertAdjacentHTML('afterend','<section class="stat" id="catalog-panel" hidden><strong>Costume workflow queue</strong><p id="catalog-status"></p><button id="compare-generations">Compare generations</button></section>');
$('#summary').insertAdjacentHTML('afterend',`<section id="workflow-live" hidden aria-label="Live costume workflow progress"><h2>725 costume workflows · live progress</h2><div class="workflow-metrics">
<div class="stat"><small>Current workflow</small><strong id="workflow-current">—</strong><p id="workflow-stage"></p></div>
<div class="stat"><small>Dogs processed · current workflow</small><strong id="workflow-dogs">—</strong><p>Unique dog inputs with a completed photo, across all rounds.</p></div>
<div class="stat"><small>Average AI score · current workflow</small><strong id="workflow-average">—</strong><p id="workflow-score-count"></p></div>
<div class="stat"><small>Photos generated · costume run</small><strong id="workflow-photos">—</strong><p id="workflow-photo-count"></p></div>
<div class="stat"><small>Workflows remaining</small><strong id="workflow-remaining">—</strong><p id="workflow-accepted"></p></div>
</div><p id="workflow-freshness"></p></section>`);
const workflowStyle=document.createElement('style');workflowStyle.textContent='#workflow-live h2{font-size:21px;margin:18px 0 12px}.workflow-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.workflow-metrics .stat strong{font-size:26px;overflow-wrap:anywhere}.workflow-metrics .stat p{font-size:13px;margin-top:8px}#workflow-current{font-size:21px}#workflow-freshness{font-size:13px;margin-top:10px}';document.head.append(workflowStyle);
function paintWorkflowProgress(){
 const progress=state.catalog_progress||{},active=state.auto_refine||{},counts=progress.counts||{};
 $('#workflow-live').hidden=!progress.total;if(!progress.total)return;
 const prefix=(progress.version||'')+'-',activeMatches=!!progress.version&&!!active.run&&active.run.startsWith(prefix);
 // Preserve totals when a new queue policy resumes the same 725-reference project.
 const rows=[...new Map(state.rows.filter(r=>r.reference_id&&r.auto_refine_version&&r.planner==='local-vision-llm-v1').map(r=>[r.id,r])).values()];
 const complete=rows.filter(r=>r.output&&r.status==='Complete');
 const currentAll=complete.filter(r=>r.template===(activeMatches?active.current_template:progress.current_reference));
 const qualified=['qualified-inputs-development-v2','qualified-inputs-85-percent-v3'].includes(progress.policy);
 const currentRows=qualified?currentAll.filter(r=>{const q=state.input_photo_scores?.[r.input];return q?.score>=7&&['medium','high'].includes(q.confidence)}):currentAll;
 const dogs=new Set(currentRows.map(r=>r.dog_id||r.input).filter(Boolean)).size;
 const scored=currentRows.map(r=>r.ai_review).filter(a=>a&&['identity','fur','body','template'].every(k=>Number.isFinite(a[k])&&a[k]>=1&&a[k]<=10));
 const average=scored.length?scored.reduce((sum,a)=>sum+(a.identity+a.fur+a.body+a.template)/4,0)/scored.length:null;
 const activeRows=rows.filter(r=>r.auto_refine_version===active.run);
 const rendering=activeRows.some(r=>r.status==='Rendering'),scoring=state.judge?.status==='Scoring'&&activeRows.some(r=>r.id===state.judge.active_row_id);
 const accepted=counts.accepted||0,remaining=Math.max(0,progress.total-accepted),stage=activeMatches?(rendering?'Rendering on GPU':scoring?'Scoring generated portrait':active.phase||active.status):progress.status;
 $('#workflow-current').textContent=(activeMatches?active.current_template:progress.current_reference)||'Preparing next workflow';
 $('#workflow-stage').textContent=(activeMatches?active.phase:stage)||'Waiting for update';
 $('#workflow-dogs').textContent=`${dogs}${activeMatches&&active.dogs?' / '+active.dogs:''}`;
 $('#workflow-average').textContent=average===null?'Awaiting scores':`${average.toFixed(1)} / 10`;
 $('#workflow-score-count').textContent=`${scored.length} scored photos${qualified?' from qualifying inputs':''} · average of face, fur, body and costume across all attempts; not a pass verdict.`;
 $('#workflow-photos').textContent=complete.length.toLocaleString();
 $('#workflow-photo-count').textContent=`${currentAll.length} for this workflow · includes retries; excludes the earlier batch.`;
 $('#workflow-remaining').textContent=`${remaining} / ${progress.total}`;
 $('#workflow-accepted').textContent=`${accepted} accepted · ${counts.blocked||0} need attention (included in remaining).`;
 const updated=activeMatches?active.updated_at:progress.updated_at,age=Number.isFinite(updated)?Math.max(0,Math.round(Date.now()/1000-updated)):null;
 $('#workflow-freshness').textContent=`Live status refreshes automatically.${age===null?'':` Worker last reported ${age}s ago.`} ${qualified?'Dog count includes only input photos scoring 7+. ':''}Dogs processed does not mean all passed.${progress.required_pass_percent===85?` Current recipe: ${progress.checked_current_recipe||0}/${progress.roster_total||0} scored; ${progress.passed_current_recipe||0} passing; ${progress.required_passing_entries||0} required (85%).`:''}`;
 $('#summary').textContent=`Costume workflow run: ${progress.status||'Waiting'} · ${accepted} / ${progress.total} accepted · ${remaining} remaining`;
 $('#notice').textContent=state.batch?.status==='Complete'?'The earlier image batch is finished. The 725-costume workflow refinement run is separate; see its live status above.':'This status tracks the 725-costume workflow refinement run. Earlier batch counts are separate.';
 $('#eta').previousElementSibling.textContent='Workflow completion time';$('#eta').textContent=remaining?'Depends on retries':'All accepted';
 $('#speed').previousElementSibling.textContent='Earlier batch render speed';
}
const generationStyle=document.createElement('style');generationStyle.textContent=`
#generation-view{padding:12px 4% 30px}#generation-view h2{margin:6px 0}#generation-view>label{margin-top:15px;flex-wrap:wrap}#generation-group{max-width:100%}.generation-context{display:flex;gap:16px;margin:18px 0;flex-wrap:wrap}.generation-context figure{margin:0;flex:0 1 190px}.generation-context img{width:100%;height:175px;object-fit:contain;background:#0c110e;border-radius:8px}.generation-context figcaption{font-size:14px}.generation-slider input{flex:1;min-width:180px;accent-color:#b1dba4}.generation-track{display:flex;gap:18px;overflow-x:auto;align-items:flex-start;scroll-snap-type:x proximity;padding:16px 0 22px;scrollbar-color:#b1dba4 #26342a}.generation-card{flex:0 0 min(440px,87vw);min-width:0;scroll-snap-align:start;padding:16px;background:#18241c;border:1px solid #526c57;border-radius:12px}.generation-card>.cell:not(:last-child){display:none}.generation-card h3{margin:0 0 8px}.generation-card .cell:before{display:none}.generation-card .cell img,.generation-card .pending{height:410px}.generation-card .ai-summary{border-top:0;padding-top:0}.generation-card .rating-form{border-top:1px solid #526c57;margin-top:14px;padding-top:14px}.generation-card .star-choice span{font-size:27px}.generation-card .review-box{padding:12px}.generation-card .auto-explanation{margin:10px 0;font-size:15px}.generation-card .ai-detail{font-size:14px}#catalog-panel{margin-top:10px}`;document.head.append(generationStyle);
const dogSections=new Map();
const generationCards=new Map();let generationKey='',generationGroupsKey='';
$('#compare-generations').onclick=()=>{$('#pack').value='all';$('#search').value='';$('#mode').value='generations';generationKey='';draw();$('#generation-view').scrollIntoView({behavior:'smooth'})};
$('#generation-group').onchange=()=>{generationKey=$('#generation-group').value;draw()};
function dogSection(key,first){
 let section=dogSections.get(key);if(section)return section;
 section=document.createElement('section');section.className='generation-dog';
 section.innerHTML='<h3 class="dog-heading"></h3><p class="dog-count"></p><p class="input-photo-quality"></p><div class="generation-context"></div><label class="generation-slider">Slide through generations for this dog <input type="range" min="0" max="0" value="0" step="1"></label><div class="generation-track" tabindex="0"></div>';
 section.querySelector('.dog-heading').textContent=first.label||'Dog';
 const track=section.querySelector('.generation-track'),slider=section.querySelector('input');
 track.setAttribute('aria-label','Generations for '+(first.label||'dog'));slider.setAttribute('aria-label','Slide generations for '+(first.label||'dog'));
 section.querySelector('.generation-context').innerHTML=[[first.input,'Original dog'],[first.prepared||first.input,'Dog reference used'],[first.reference,'Costume reference']].map(([file,label])=>`<figure><a href="${media(file)}" target="_blank" rel="noopener"><img loading="lazy" src="${media(file)}" alt="${label}"></a><figcaption>${label}</figcaption></figure>`).join('');
 slider.oninput=()=>{const available=Math.max(0,track.scrollWidth-track.clientWidth);track.scrollTo({left:available*Number(slider.value)/Math.max(1,Number(slider.max)),behavior:'smooth'})};
 track.onscroll=()=>{const available=track.scrollWidth-track.clientWidth;slider.value=available>0?Math.round(track.scrollLeft/available*Number(slider.max)):0};
 dogSections.set(key,section);return section;
}
const dogStyle=document.createElement('style');dogStyle.textContent='.generation-dog{border-top:2px solid #526c57;margin-top:28px;padding-top:20px;min-width:0}.dog-heading{font-size:24px;margin:0 0 6px}.generation-track{position:relative}.generation-dog .generation-slider{display:flex;gap:12px;flex-wrap:wrap}';document.head.append(dogStyle);
const drawWithReviews=draw;
draw=function(){
drawWithReviews();
paintWorkflowProgress();
const progress=state.catalog_progress||{},counts=progress.counts||{};$('#catalog-panel').hidden=!progress.total;
$('#catalog-status').textContent=progress.total?`${progress.status} · ${progress.total} costumes · ${counts.accepted||0} accepted · ${counts.in_progress||0} started / resumable · ${counts.retry_pending||0} awaiting more experiments · ${counts.pending||0} not started · ${counts.blocked||0} need attention. ${progress.current_reference?'Current: '+progress.current_reference+'. ':''}Workflows are being optimized; model weights remain unchanged.`:'';
const activeRun=state.auto_refine||{};
if(progress.total&&activeRun.run&&activeRun.run.startsWith((progress.version||'')+'-')){
 const runRows=(state.rows||[]).filter(r=>r.auto_refine_version===activeRun.run);
 const rendering=runRows.some(r=>r.status==='Rendering');
 const scoring=runRows.some(r=>r.id===state.judge?.active_row_id)&&state.judge?.status==='Scoring';
 const phase=rendering?'Rendering on GPU':scoring?'Scoring generated portrait':activeRun.phase||activeRun.status||'Waiting for update';
 const age=Number.isFinite(activeRun.updated_at)?Math.max(0,Math.round(Date.now()/1000-activeRun.updated_at)):null;
 $('#catalog-status').textContent+=` Current round: ${activeRun.generations||0} renders submitted. Stage: ${phase}.${age===null?'':` Stage updated ${age}s ago.`} Accepted counts fully validated costume workflows, not individual images.`;
}
const enabled=$('#mode').value==='generations';$('#generation-view').hidden=!enabled;$('#rows').hidden=enabled;document.querySelector('.labels').hidden=enabled;$('#pages').hidden=enabled;if(!enabled)return;
const groups=new Map();for(const r of filtered().filter(r=>r.auto_refine_version)){const key=JSON.stringify([r.pack,r.template]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r)}
const entries=[...groups].sort((a,b)=>Math.max(...b[1].map(r=>r.started||0))-Math.max(...a[1].map(r=>r.started||0)));
if(!groups.has(generationKey))generationKey=entries[0]?.[0]||'';
const optionsKey=JSON.stringify(entries.map(([k,rows])=>[k,rows.length]));if(optionsKey!==generationGroupsKey){generationGroupsKey=optionsKey;$('#generation-group').innerHTML=entries.map(([key,rows])=>`<option value="${esc(key)}">${esc(rows[0].template)} | ${new Set(rows.map(r=>r.input)).size} dogs | ${rows.length} generations</option>`).join('')}$('#generation-group').value=generationKey;
const workflowRows=(groups.get(generationKey)||[]).sort((a,b)=>(a.started||a.finished_at||0)-(b.started||b.finished_at||0)||a.id.localeCompare(b.id));
const dogs=new Map();for(const r of workflowRows){const key=JSON.stringify([generationKey,r.input]);if(!dogs.has(key))dogs.set(key,[]);dogs.get(key).push(r)}
$('#generation-count').textContent=workflowRows.length?`${dogs.size} dog rows | ${workflowRows.length} generations. Each row scrolls independently. Earlier heuristic attempts are labeled.`:'No automatic generations match these filters yet.';
for(const [key,section] of dogSections)if(!dogs.has(key))section.remove();
let dogIndex=0;
for(const [key,rows] of dogs){
const section=dogSection(key,rows[0]),host=$('#generation-dogs');if(host.children[dogIndex]!==section)host.insertBefore(section,host.children[dogIndex]||null);dogIndex++;
const track=section.querySelector('.generation-track'),slider=section.querySelector('input');section.querySelector('.dog-count').textContent=`${rows.length} generations for this dog`;
const inputScore=state.input_photo_scores?.[rows[0].input];
section.querySelector('.input-photo-quality').textContent=inputScore?.score?`Input photo: ${inputScore.score}/10 · Face visibility ${inputScore.face}, coat detail ${inputScore.fur}, body visibility ${inputScore.body}. ${inputScore.score>=7&&inputScore.confidence!=='low'?'Qualifies for workflow checks.':'Clearer customer photo recommended; excluded from workflow acceptance.'} ${inputScore.reason} ${inputScore.suggestion}`:'Input photo quality: awaiting separate source-only audit.';
const keep=new Set(rows.map(r=>r.id));for(const card of [...track.children])if(!keep.has(card.current?.id))card.remove();
rows.forEach((r,i)=>{let card=generationCards.get(r.id);if(!card){card=document.createElement('article');card.className='generation-card';card.innerHTML='<div class="cell"></div><div class="cell"></div><div class="cell"><h3></h3><a class="generation-output" target="_blank" rel="noopener"><img loading="lazy" hidden alt="Generated portrait"></a><div class="pending"></div><p class="generation-meta"></p></div>';makeReview(card,r);const box=card.querySelector('.review-box');box.insertBefore(card.querySelector('.ai-summary'),card.querySelector('form'));const explanation=card.querySelector('.auto-explanation');if(explanation)explanation.open=true;generationCards.set(r.id,card);track.append(card)}
if(track.children[i]!==card)track.insertBefore(card,track.children[i]||null);
card.current=r;card.querySelector('h3').textContent=`Generation ${i+1}`;
const file=r.thumbnail||r.output||r.preview,img=card.querySelector('.generation-output img'),pending=card.querySelector('.cell:last-child>.pending');img.hidden=!file;pending.hidden=!!file;pending.textContent=r.status;
if(file){const src=media(file)+(r.output?'':'?v='+(r.progress_seq||0));if(img.getAttribute('src')!==src)img.src=src;card.querySelector('.generation-output').href=media(r.output||r.preview||file)}
card.querySelector('.generation-meta').textContent=`${r.status} · ${r.planner==='local-vision-llm-v1'?'Local LLM planned':'Earlier heuristic workflow'} · ${r.auto_stage||'tune'}${r.seconds?' · '+r.seconds+'s':''}`;paintReview(card,r);
});
slider.max=Math.max(0,rows.length-1);slider.disabled=rows.length<2;
}
};
$('#mode').value='generations';
