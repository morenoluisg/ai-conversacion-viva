'use strict';
(()=>{
 const defaults={...window.appBranding};
 const catalog=themes.map((t,i)=>({id:String(i),name:t[0],color:t[1],keywords:t[2]}));
 const groups=categories=>[
  {id:'environment',name:'Ambiente y recursos',categories:['0','1','2']},
  {id:'society',name:'Comunidades y decisiones',categories:['3','5']},
  {id:'technology',name:'Datos y tecnología',categories:['4']}
 ].map(g=>({...g,categories:g.categories.filter(id=>categories.some(c=>c.id===id))})).filter(g=>g.categories.length);
 let records=[],serial=0,generation=0,pending=0;
 const automaticCatalog=()=>catalog.filter(c=>records.some(e=>e.concepts.some(concept=>catalog[concept.theme]?.id===c.id)));
 const settings=categories=>({categories,groups:groups(categories)});
 function classified(event,lens){
  const categories=lens==='automatic'?automaticCatalog():catalog;
  return {...event,categories,settings:settings(categories),method:'demo-simulated',concepts:event.concepts.slice(0,3).map(c=>({...c,theme:categories.findIndex(v=>v.id===catalog[c.theme]?.id)})).filter(c=>c.theme>=0)};
 }
 function complete(event){return {...classified(event,'manual'),lenses:{agenda:classified(event,'agenda'),automatic:classified(event,'automatic')}}}
 function source(){updateLensSource(lensState[activeLens]?.events.at(-1)?.method);$('source').textContent='DEMOSTRACIÓN SIMULADA';$('demoAnalysis').textContent=pending?'Texto incorporado · Simulando análisis de temas…':'Temas simulados actualizados';}
 function emit(text,concepts,speaker='Ejemplo simulado'){
  const event={id:'pages-'+(++serial),text,speaker,concepts,categories:catalog};records.push(event);
  if(records.length>150)records.shift();
  const initial=complete(event);initial.lenses.automatic={...initial.lenses.automatic,concepts:[],method:'analysis-pending'};
  const wasPlaying=playing;consumeMessage({type:'event',event:initial});playing=wasPlaying;pending++;source();
  const token=generation;
  setTimeout(()=>{if(token!==generation)return;const resume=playing;consumeMessage({type:'event_update',event:complete(event)});playing=resume;pending--;source()},650);
 }
 function snapshot(){
  const all=records.map(complete);
  consumeMessage({type:'snapshot',settings:settings(catalog),events:all,lenses:{agenda:{settings:settings(catalog),events:all.map(e=>e.lenses.agenda)},automatic:{settings:settings(automaticCatalog()),events:all.map(e=>e.lenses.automatic)}}});
  source();
 }
 for(let i=0;i<5;i++){const [text,labels,gs]=script[i];records.push({id:'pages-'+(++serial),text,speaker:'Ejemplo simulado',concepts:labels.map((label,j)=>({label,theme:gs[j]})),categories:catalog})}
 snapshot();playing=true;idx=5;last=performance.now();
 step=function(){if(idx>=script.length){playing=false;$('play').textContent='Reproducir';return}const [text,labels,gs]=script[idx++];emit(text,labels.map((label,i)=>({label,theme:gs[i]})));last=performance.now()};
 $('next').onclick=()=>step();
 $('reset').onclick=()=>{generation++;pending=0;records=[];serial=0;themePage=0;displaySelections.clear();clearLive();snapshot();idx=0;playing=true;$('play').textContent='Pausar';step()};
 window.demoIngest=event=>{playing=false;$('play').textContent='Reproducir';emit(event.text,infer(event.text),event.speaker||'Texto de prueba')};
 $('add').onclick=()=>{const text=$('text').value.trim();if(text){window.demoIngest({text});$('text').value=''}};
 $('text').onkeydown=e=>{if(e.key==='Enter')$('add').onclick()};
 const originalSwitch=switchLens;
 switchLens=function(lens){const wasPlaying=playing;originalSwitch(lens);playing=wasPlaying;source()};
 $('lensSelector').onchange=()=>switchLens($('lensSelector').value);
 $('demoTheme').onchange=()=>setTheme($('demoTheme').value);
 const dialog=document.createElement('dialog');dialog.className='demo-dialog';dialog.setAttribute('aria-label','Identidad de la demostración');
 const title=document.createElement('h2');title.textContent='Identidad y presentación';
 const note=document.createElement('p');note.textContent='Vista previa local: los campos se aplican al tablero al guardar. La demo no envía estos valores a un servidor. Deepgram, DeepSeek y la captura del sistema requieren la aplicación local.';
 const form=document.createElement('form'),fields=document.createElement('div');fields.className='demo-fields';
 const names={app_name:'Nombre de la aplicación',organization:'Organización o evento',description:'Descripción',center_top:'Texto central · primera línea',center_bottom:'Texto central · segunda línea',panel_heading:'Encabezado del texto',accent_color:'Color de identidad'};
 const limits={app_name:80,organization:120,description:180,center_top:24,center_bottom:24,panel_heading:100};
 for(const [key,name] of Object.entries(names)){const label=document.createElement('label'),input=document.createElement('input');input.id='demoBrand_'+key;input.name=key;input.type=key==='accent_color'?'color':'text';input.required=true;if(limits[key])input.maxLength=limits[key];label.htmlFor=input.id;label.textContent=name;fields.append(label,input)}
 const actions=document.createElement('div');actions.className='demo-actions';
 const apply=document.createElement('button');apply.type='submit';apply.textContent='Aplicar al tablero';
 const restore=document.createElement('button');restore.type='button';restore.textContent='Ejemplo ambiental';restore.onclick=()=>fill(defaults);
 const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cerrar';cancel.onclick=()=>dialog.close();
 actions.append(apply,restore,cancel);form.append(fields,actions);dialog.append(title,note,form);document.body.append(dialog);
 function fill(value){for(const key of Object.keys(names))$('demoBrand_'+key).value=value[key]}
 $('demoSettings').onclick=()=>{fill(window.appBranding);dialog.showModal()};
 form.onsubmit=e=>{e.preventDefault();const value=Object.fromEntries(Object.keys(names).map(key=>[key,$('demoBrand_'+key).value.trim()]));if(Object.values(value).some(v=>!v))return;window.setBranding(value);dialog.close()};
 document.addEventListener('keydown',e=>{if(dialog.open)e.stopImmediatePropagation()},true);
 source();
})();
