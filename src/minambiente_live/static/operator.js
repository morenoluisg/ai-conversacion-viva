'use strict';
const $=id=>document.getElementById(id);
const requestedSession=new URLSearchParams(location.search).get('session');
const sid=requestedSession&&/^[A-Za-z0-9_-]{1,64}$/.test(requestedSession)?requestedSession:localStorage.getItem('minambiente-session')||('charla-'+crypto.randomUUID().slice(0,8));
localStorage.setItem('minambiente-session',sid);
const channel=new BroadcastChannel('minambiente-'+sid);
const wsURL=path=>(location.protocol==='https:'?'wss://':'ws://')+location.host+path;
$('open').href='/visual?live=1&lens=agenda&session='+encodeURIComponent(sid);
$('session').textContent='Sesión: '+sid;
$('api').textContent='POST '+location.origin+'/api/sessions/'+sid+'/text   {"text":"Agua y biodiversidad","speaker":"Ponente"}';
let capturing=false,analysisPending=0,reportBusy=false;
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error)}
const audioClient=window.initAudioCapture({session:sid,onState:active=>{capturing=active;$('generateReport').disabled=capturing||analysisPending>0||reportBusy}});
$('view').onchange=()=>sendDisplay({view:$('view').value});
function addTranscript(ev){const p=document.createElement('p'),small=document.createElement('small');p.dataset.eventId=ev.id;small.textContent=ev.speaker+' · '+(ev.method||'')+'\n';p.append(small,document.createTextNode(ev.text));$('transcript').append(p);while($('transcript').children.length>150)$('transcript').firstChild.remove();$('transcript').scrollTop=$('transcript').scrollHeight;}
let viewer,retry;
function connectViewer(){viewer=new WebSocket(wsURL('/ws/view/'+sid));viewer.onmessage=e=>{const m=JSON.parse(e.data);if(m.branding)window.setBranding(m.branding);if(m.analysis)showAnalysis(m.analysis);if(m.type==='event_update'){const row=[...$('transcript').children].find(p=>p.dataset.eventId===m.event.id);if(row?.firstChild)row.firstChild.textContent=m.event.speaker+' · '+m.event.method+'\n';if(m.event.lenses)renderLenses(Object.fromEntries(Object.entries(m.event.lenses).map(([key,event])=>[key,{settings:event.settings,events:[event]}])))}if(m.type==='snapshot'){if(m.display?.theme)$('backgroundTheme').value=m.display.theme;$('transcript').replaceChildren();m.events.forEach(addTranscript);if(m.lenses)renderLenses(m.lenses)}if(m.type==='display'&&m.theme){$('backgroundTheme').value=m.theme;$('themeStatus').textContent='Fondo '+(m.theme==='dark'?'oscuro':'claro')+' aplicado a la sesión.'}if(m.type==='event'){addTranscript(m.event);if(m.event.lenses)renderLenses(Object.fromEntries(Object.entries(m.event.lenses).map(([key,event])=>[key,{settings:event.settings,events:[event]}])));for(const c of m.event.categories||[]){if(!categorySettings.categories.some(x=>x.id===c.id)){categorySettings.categories.push(c);renderCategories()}}}if(m.type==='reset'){$('transcript').replaceChildren();$('partial').textContent=''}};viewer.onclose=()=>{retry=setTimeout(connectViewer,1500)}}connectViewer();
setInterval(()=>{if(viewer?.readyState===WebSocket.OPEN)viewer.send('ping')},20000);
$('sendText').onclick=async()=>{const text=$('manual').value.trim();if(!text)return;try{const r=await fetch('/api/sessions/'+sid+'/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});if(!r.ok)throw Error('No se pudo enviar el fragmento');$('manual').value='';status('Fragmento incorporado.')}catch(e){status(e.message,true)}};
$('reset').onclick=async()=>{try{const r=await fetch('/api/sessions/'+sid,{method:'DELETE'});if(!r.ok)throw Error('No se pudo vaciar la sesión');status('Sesión vacía.')}catch(e){status(e.message,true)}};
$('download').onclick=async()=>{const response=await fetch('/api/sessions/'+sid+'/events');if(!response.ok)return status('No se pudo exportar.',true);const data=await response.json();const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=sid+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),500)};
window.addEventListener('beforeunload',()=>{audioClient.dispose();viewer?.close();channel.close()});

let categorySettings={categories:[],agenda:'',emergent:false};
async function categoryRequest(path,method='GET',body){const r=await fetch('/api/sessions/'+sid+path,{method,headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok)throw Error(data.detail||'No se pudo guardar');return data;}
function renderCategories(){
 renderNamedGroups();
 $('categoryList').replaceChildren();$('projectionCategories').replaceChildren();
 for(const c of categorySettings.categories){
  const row=document.createElement('div');row.style.cssText='display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0';
  const name=document.createElement('input');name.value=c.name;name.maxLength=60;name.setAttribute('aria-label','Nombre de categoría');name.style.width='220px';name.oninput=()=>c.name=name.value;
  const color=document.createElement('input');color.type='color';color.value=c.color;color.style.cssText='width:65px;height:45px;padding:4px';color.setAttribute('aria-label','Color de '+c.name);color.oninput=()=>c.color=color.value;
  const keywords=document.createElement('input');keywords.value=c.keywords.join(', ');keywords.placeholder='Palabras clave separadas por comas';keywords.setAttribute('aria-label','Palabras clave de '+c.name);keywords.style.width='300px';keywords.oninput=()=>c.keywords=keywords.value.split(',').map(k=>k.trim()).filter(Boolean);
  const remove=document.createElement('button');remove.textContent='Quitar';remove.className='secondary';remove.onclick=()=>{categorySettings.categories=categorySettings.categories.filter(x=>x.id!==c.id);renderCategories()};
  const origin=document.createElement('small');origin.textContent=c.origin==='emergent'?'Emergente':c.origin==='agenda'?'Agenda':'Manual';row.append(name,color,keywords,origin,remove);$('categoryList').append(row);
  const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.value=c.id;check.checked=true;label.style.cssText='display:inline-block;margin:8px 16px 8px 0';label.append(check,document.createTextNode(' '+c.name));$('projectionCategories').append(label);
 }
}
function settingsBody(){return {...categorySettings,agenda:$('agenda').value,emergent:$('emergent').checked}}
let brandingOptions=null;
const brandingLabels={app_name:'Nombre de la aplicación',organization:'Organización o evento',description:'Descripción de presentación',center_top:'Texto central · primera línea',center_bottom:'Texto central · segunda línea',panel_heading:'Encabezado del panel de texto',accent_color:'Color de identidad'};
const brandingLimits={app_name:80,organization:120,description:180,center_top:24,center_bottom:24,panel_heading:100};
function brandingDraft(){return Object.fromEntries(Object.keys(brandingLabels).map(key=>[key,$('brand_'+key).value.trim()]))}
function previewBranding(){const value=brandingDraft();$('previewOrganization').textContent=value.organization;$('previewName').textContent=value.app_name;$('previewDescription').textContent=value.description;$('previewCenter').textContent=value.center_top+' / '+value.center_bottom;$('previewPanel').textContent=value.panel_heading;$('brandingPreview').style.borderColor=value.accent_color}
function fillBranding(value){for(const key of Object.keys(brandingLabels))$('brand_'+key).value=value[key];previewBranding()}
for(const [key,name] of Object.entries(brandingLabels)){const label=document.createElement('label'),input=document.createElement('input');label.htmlFor='brand_'+key;label.textContent=name;input.id='brand_'+key;input.type=key==='accent_color'?'color':'text';if(brandingLimits[key])input.maxLength=brandingLimits[key];input.required=true;input.oninput=previewBranding;$('brandingFields').append(label,input)}
fillBranding(window.appBranding);
categoryRequest('/branding').then(data=>{brandingOptions=data;fillBranding(data.current);window.setBranding(data.current)}).catch(e=>$('brandingStatus').textContent=e.message);
$('defaultBranding').onclick=()=>{if(brandingOptions)fillBranding(brandingOptions.defaults)};
$('environmentalBranding').onclick=()=>{if(brandingOptions)fillBranding(brandingOptions.environmental)};
$('saveBranding').onclick=async()=>{const draft=brandingDraft();if(Object.values(draft).some(v=>!v)){$('brandingStatus').textContent='Completa todos los campos de identidad.';return}const button=$('saveBranding');button.disabled=true;try{const saved=await categoryRequest('/branding','PUT',draft);window.setBranding(saved);$('brandingStatus').textContent='Identidad aplicada a esta sesión y sus tableros. Se usará en los próximos informes.'}catch{$('brandingStatus').textContent='No se pudo guardar la identidad. Revisa los campos y la conexión.'}finally{button.disabled=false}};
categoryRequest('/settings').then(data=>{categorySettings=data;$('agenda').value=data.agenda;$('emergent').checked=data.emergent;renderCategories()}).catch(e=>$('categoryStatus').textContent=e.message);
$('newCategory').onclick=()=>{if(categorySettings.categories.length>=24)return;categorySettings.categories.push({id:crypto.randomUUID(),name:'Nueva categoría',color:'#2567b2',keywords:[],origin:'manual'});renderCategories()};
$('saveCategories').onclick=async()=>{try{categorySettings=await categoryRequest('/settings','PUT',settingsBody());renderCategories();$('categoryStatus').textContent='Configuración guardada y mapas actualizados.'}catch(e){$('categoryStatus').textContent=e.message}};
$('inferCategories').onclick=async()=>{const b=$('inferCategories');b.disabled=true;$('categoryStatus').textContent='Analizando la agenda…';try{const data=await categoryRequest('/infer-categories','POST',settingsBody());categorySettings.categories=data.categories;renderCategories();$('categoryStatus').textContent='Propuesta lista para revisar. Pulsa Guardar categorías para aplicarla.'}catch(e){$('categoryStatus').textContent=e.message}finally{b.disabled=false}};
$('allCategories').onclick=()=>document.querySelectorAll('#projectionCategories input').forEach(c=>c.checked=true);
$('projectGroup').onclick=()=>{const ids=[...document.querySelectorAll('#projectionCategories input:checked')].map(c=>c.value);if(!ids.length){$('categoryStatus').textContent='Selecciona al menos una categoría.';return}const url=new URL('/visual',location.origin);url.search=new URLSearchParams({live:'1',session:sid,view:$('view').value,categories:ids.join(',')});window.open(url,'_blank','noopener')};

let reportTimer;
function displayReport(state){
 const busy=state.status==='running';reportBusy=busy;$('generateReport').disabled=busy||capturing||analysisPending>0;
 $('reportStatus').textContent=state.message+(state.lens?' · Lectura: '+({agenda:'Agenda',manual:'Editable',automatic:'DeepSeek autónomo'}[state.lens]||state.lens):'')+(state.fragments?' · '+state.fragments+' fragmentos':'')+(state.warnings?.length?' · Algunas secciones no tienen análisis de IA; revisa las advertencias de los documentos.':'');
 $('downloadReport').hidden=state.status!=='ready';
 $('downloadReport').href='/api/sessions/'+sid+'/export/download';
 clearTimeout(reportTimer);if(busy)reportTimer=setTimeout(checkReport,2000);
}
async function checkReport(){try{const r=await fetch('/api/sessions/'+sid+'/export/status');if(!r.ok)throw Error('No se pudo consultar el estado');displayReport(await r.json())}catch(e){$('reportStatus').textContent=e.message+'. Reintentando…';reportTimer=setTimeout(checkReport,5000)}}
$('generateReport').onclick=async()=>{if(capturing){$('reportStatus').textContent='Detén la captura antes de generar el cierre.';return}$('generateReport').disabled=true;$('downloadReport').hidden=true;try{const r=await fetch('/api/sessions/'+sid+'/export?'+new URLSearchParams({lens:$('lensMode').value}),{method:'POST'}),data=await r.json();if(!r.ok)throw Error(data.detail||'No se pudo generar el informe');displayReport(data)}catch(e){$('reportStatus').textContent=e.message;$('generateReport').disabled=false}};
checkReport();

function renderNamedGroups(){
 if(!categorySettings.groups?.length)categorySettings.groups=Array.from({length:3},(_,i)=>({id:'grupo-'+(i+1),name:'Grupo '+(i+1),categories:categorySettings.categories.filter((_,n)=>n%3===i).map(c=>c.id)}));
 $('namedGroups').replaceChildren();
 for(const group of categorySettings.groups){
  group.categories=group.categories.filter(id=>categorySettings.categories.some(c=>c.id===id));
  const box=document.createElement('fieldset'),name=document.createElement('input');name.value=group.name;name.maxLength=60;name.setAttribute('aria-label','Nombre del grupo');name.oninput=()=>group.name=name.value;box.append(name);box.style.cssText='border:1px solid #c8d7ce;padding:14px;margin:10px 0';
  for(const c of categorySettings.categories){const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=group.categories.includes(c.id);check.onchange=()=>{group.categories=check.checked?[...new Set([...group.categories,c.id])]:group.categories.filter(id=>id!==c.id)};label.style.cssText='display:inline-block;margin:8px 12px 0 0;font-weight:400';label.append(check,document.createTextNode(' '+c.name));box.append(label)}
  const link=document.createElement('a');link.className='button';link.target='_blank';link.rel='noopener';link.textContent='Guardar y abrir este grupo';link.href='/visual?'+new URLSearchParams({live:'1',session:sid,group:group.id});link.onclick=async event=>{event.preventDefault();const target=window.open('about:blank','_blank');if(target)target.opener=null;try{categorySettings=await categoryRequest('/settings','PUT',settingsBody());if(target)target.location.href=link.href;else $('categoryStatus').textContent='Grupo guardado. Permite las ventanas emergentes y vuelve a abrirlo.'}catch(e){target?.close();$('categoryStatus').textContent=e.message}};box.append(link);$('namedGroups').append(box);
 }
}
$('openThreeGroups').onclick=async()=>{try{categorySettings=await categoryRequest('/settings','PUT',settingsBody());renderCategories();$('categoryStatus').textContent='Grupos guardados. Abre cada enlace de grupo para proyectarlos simultáneamente.';for(const group of categorySettings.groups){const link=[...$('namedGroups').querySelectorAll('a')].find(a=>new URL(a.href).searchParams.get('group')===group.id);if(link)link.style.outline='2px solid #287a38'}}catch(e){$('categoryStatus').textContent=e.message}};

function renderLenses(lenses){
 for(const [key,id] of [['agenda','agendaLensContent'],['automatic','autoLensContent']]){
  const state=lenses[key];if(!state)continue;const box=$(id);box.replaceChildren();
  if(!state.settings.categories.length){box.textContent=state.events?.at(-1)?.method==='deepseek-auto-unavailable'?'DeepSeek no respondió. Texto conservado; se reintentará con la próxima intervención.':'Aún no hay temas emergentes. Esperando intervenciones y respuesta de DeepSeek.';continue}
  for(const group of state.settings.groups){const p=document.createElement('p');p.textContent=group.name+': '+group.categories.map(id=>state.settings.categories.find(c=>c.id===id)?.name).filter(Boolean).join(' · ');box.append(p)}
  if(state.events?.at(-1)?.method==='deepseek-auto-unavailable'){const p=document.createElement('p');p.textContent='DeepSeek no respondió con una agrupación válida. La conversación se conserva y se reintentará con la próxima intervención.';box.append(p)}
 }
}
$('lensMode').onchange=()=>{const mode=$('lensMode').value;$('open').href='/visual?'+new URLSearchParams({live:'1',session:sid,lens:mode});for(const [key,id] of [['agenda','agendaLens'],['manual','manualLens'],['automatic','autoLens']])$(id).hidden=key!==mode;sendDisplay({lens:mode})};
$('openLens').onclick=()=>window.open('/visual?'+new URLSearchParams({live:'1',session:sid,lens:$('lensMode').value,view:$('view').value}),'_blank','noopener');
fetch('/api/sessions/'+sid+'/lenses').then(r=>r.json()).then(renderLenses).catch(()=>{$('autoLensContent').textContent='No se pudo consultar el estado de las lecturas.'});

$('remoteCapture').href='/captura?'+new URLSearchParams({session:sid});
$('serverSetup').href='/servidor?'+new URLSearchParams({session:sid});
$('captureLink').value=new URL($('remoteCapture').href,location.origin).href;
$('copyCaptureLink').onclick=async()=>{try{await navigator.clipboard.writeText($('captureLink').value);$('linkStatus').textContent='Enlace copiado. Compártelo con el operador de audio.'}catch{$('captureLink').select();$('linkStatus').textContent='Selecciona y copia el enlace de captura.'}};

async function sendDisplay(change){try{const r=await fetch('/api/sessions/'+sid+'/display',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(change)});if(!r.ok)throw Error('No se pudo actualizar la pantalla remota.');$('linkStatus').textContent='Pantallas de la sesión actualizadas.'}catch(e){$('linkStatus').textContent=e.message}}

$('backgroundTheme').onchange=async()=>{const theme=$('backgroundTheme').value;$('themeStatus').textContent='Aplicando fondo…';try{const r=await fetch('/api/sessions/'+sid+'/display',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({theme})});if(!r.ok)throw Error('No se pudo cambiar el fondo.');$('themeStatus').textContent='Fondo '+(theme==='dark'?'oscuro':'claro')+' aplicado a los tableros.'}catch(e){$('themeStatus').textContent=e.message}};

function showAnalysis(state){analysisPending=state.pending;$('analysisStatus').textContent=state.pending?'Transcripción guardada. Temas pendientes: '+state.pending+'. Último análisis: '+state.last_seconds+' s.':'Temas actualizados. Último análisis: '+state.last_seconds+' s.';if(state.failures)$('analysisStatus').textContent+=' Clasificaciones no disponibles: '+state.failures+'. Texto conservado.';$('generateReport').disabled=capturing||state.pending>0||reportBusy}
setInterval(async()=>{try{const response=await fetch('/api/sessions/'+sid+'/status');if(response.ok){const state=await response.json();if(state.analysis)showAnalysis(state.analysis)}}catch{}},3000);
