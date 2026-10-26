'use strict';
const $=id=>document.getElementById(id);
const sid=localStorage.getItem('minambiente-session')||('charla-'+crypto.randomUUID().slice(0,8));
localStorage.setItem('minambiente-session',sid);
const channel=new BroadcastChannel('minambiente-'+sid);
const wsURL=path=>(location.protocol==='https:'?'wss://':'ws://')+location.host+path;
$('open').href='/visual?live=1&session='+encodeURIComponent(sid);
$('session').textContent='Sesión: '+sid;
$('api').textContent='POST '+location.origin+'/api/sessions/'+sid+'/text   {"text":"Agua y biodiversidad","speaker":"Ponente"}';
let config={},socket=null,context=null,worklet=null,streams=[],sources=[],capturing=false,stopping=false,flushResolve=null,stopResolve=null,readyResolve=null;
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error)}
function sourceHint(){const val=$('source').value;$('includeMic').disabled=val==='mic';$('sourceHint').textContent=val==='mic'?'Usa el micrófono del salón o de tu computador.':val==='tab'?'En el selector elige la pestaña de Teams y marca Compartir audio.':'En el selector elige Pantalla completa y Compartir audio del sistema, si el navegador lo ofrece.'}
function providerHint(){const val=$('provider').value;$('warmup').disabled=capturing||val!=='local';$('providerHint').textContent=val==='local'?'Modelo '+(config.model||'base')+'. Procesa bloques de unos 6 segundos. La primera preparación descarga el modelo.':'Audio enviado a Deepgram. Requiere una clave configurada en el archivo .env del servidor.'}
$('source').onchange=sourceHint;$('provider').onchange=providerHint;sourceHint();
fetch('/api/config').then(r=>r.json()).then(data=>{config=data;$('provider').value=data.default_stt;providerHint();$('conceptHint').textContent=data.concept_provider==='ollama'?'Conceptos: Ollama local, con reglas de respaldo si no responde.':'Conceptos: reglas del vocabulario ambiental. Puedes activar Ollama en .env.';status('Servidor disponible. Elige la fuente y abre la visualización.');}).catch(()=>status('No se puede acceder al servidor local.',true));
function controls(active){capturing=active;$('start').disabled=active;$('stop').disabled=!active;$('source').disabled=active;$('provider').disabled=active;$('reset').disabled=active;$('includeMic').disabled=active||$('source').value==='mic';providerHint()}
async function cleanup(){for(const stream of streams)for(const track of stream.getTracks())track.stop();streams=[];for(const node of sources){try{node.disconnect()}catch{}}sources=[];if(worklet){try{worklet.disconnect()}catch{}}worklet=null;if(context){try{await context.close()}catch{}}context=null;$('bar').style.width='0%'}
function waitSocket(ws){return new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',()=>reject(Error('No se pudo abrir el canal de audio.')),{once:true});});}
async function start(){
  if(capturing)return;
  if(!navigator.mediaDevices?.getUserMedia) return status('Abre esta página en Chrome o Edge en localhost.',true);
  controls(true);stopping=false;status('Selecciona la fuente y concede acceso al audio.');
  try{
    const src=$('source').value;
    if(src!=='mic'){
      if(!navigator.mediaDevices.getDisplayMedia)throw Error('Este navegador no permite compartir audio de pantalla. Prueba Chrome o Edge.');
      const shared=await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:src==='tab'?'browser':'monitor'},audio:{suppressLocalAudioPlayback:false},systemAudio:'include',selfBrowserSurface:'exclude',surfaceSwitching:'exclude'});
      streams.push(shared);
      if(!shared.getAudioTracks().length)throw Error('La fuente no incluye audio. Vuelve a elegir la pestaña o pantalla y activa Compartir audio. Si no aparece, usa Teams web.');
    }
    if(src==='mic'||$('includeMic').checked){streams.push(await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false}));}
    for(const stream of streams)for(const track of stream.getTracks())track.onended=()=>{if(capturing&&!stopping)stop()};
    context=new AudioContext({sampleRate:48000});await context.resume();
    await context.audioWorklet.addModule('/static/audio-worklet.js');
    socket=new WebSocket(wsURL('/ws/audio/'+sid));socket.binaryType='arraybuffer';
    const ws=socket;
    const ready=new Promise((resolve,reject)=>{readyResolve={resolve,reject};});ready.catch(()=>{});
    ws.onmessage=event=>{const msg=JSON.parse(event.data);
      if(msg.type==='ready'){readyResolve?.resolve();readyResolve=null;status('Capturando audio. La visualización recibirá texto confirmado.');}
      if(msg.type==='status')status(msg.message);
      if(msg.type==='partial')$('partial').textContent=msg.text;
      if(msg.type==='transcript')status('Texto reconocido. Analizando conceptos…');
      if(msg.type==='published')status('Texto y conceptos incorporados a la pantalla.'+(msg.pending?' Pendientes: '+msg.pending:''));
      if(msg.type==='stopped'){stopResolve?.();stopResolve=null;}
      if(msg.type==='error'){status(msg.message,true);readyResolve?.reject(Error(msg.message));readyResolve=null;stopResolve?.();stopResolve=null;cleanup().then(()=>controls(false));}
    };
    ws.onclose=()=>{readyResolve?.reject(Error('La conexión de audio se cerró.'));readyResolve=null;stopResolve?.();stopResolve=null;if(capturing&&!stopping){status('La conexión terminó. La captura está detenida.',true);cleanup().then(()=>controls(false));}};
    await waitSocket(ws);
    ws.send(JSON.stringify({provider:$('provider').value,sample_rate:16000}));
    status('Preparando transcripción. Espera la confirmación antes de hablar.');
    await ready;
    worklet=new AudioWorkletNode(context,'pcm16-capture',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]});
    worklet.port.onmessage=event=>{const data=event.data;if(data.flushed){flushResolve?.();flushResolve=null;return}if(data.pcm&&ws.readyState===WebSocket.OPEN){if(ws.bufferedAmount>1024*1024){status('El envío de audio está retrasado. Deteniendo para evitar pérdida de sincronía.',true);stop();return}ws.send(data.pcm);$('bar').style.width=Math.min(100,data.rms*500)+'%';$('signal').textContent=data.rms>.001?'Audio detectado.':'Sin señal de voz. Comprueba Compartir audio y el micrófono.';}};
    // Solo conectamos las pistas de audio. El video requerido por el selector nunca se envía.
    const gain=1/Math.max(1,streams.length);
    for(const stream of streams){const onlyAudio=new MediaStream(stream.getAudioTracks()),source=context.createMediaStreamSource(onlyAudio),level=context.createGain();level.gain.value=gain;source.connect(level);level.connect(worklet);sources.push(source,level);}
    worklet.connect(context.destination); // el procesador entrega ceros, evita eco.
  }catch(error){readyResolve=null;if(socket){try{socket.close()}catch{}}await cleanup();controls(false);status(error.message||String(error),true)}
}
async function stop(){
  if(!capturing||stopping)return;
  stopping=true;if(readyResolve){readyResolve.reject(Error('Captura cancelada antes de iniciar.'));readyResolve=null;socket?.close();await cleanup();controls(false);stopping=false;return}$('stop').disabled=true;status('Deteniendo captura y procesando el último fragmento…');
  const ws=socket;
  if(worklet){await Promise.race([new Promise(r=>{flushResolve=r;worklet.port.postMessage('flush')}),new Promise(r=>setTimeout(r,750))]);}
  await cleanup();
  if(ws&&ws.readyState===WebSocket.OPEN){
    const stopped=new Promise(r=>{stopResolve=r});ws.send(JSON.stringify({type:'stop'}));
    await Promise.race([stopped,new Promise(r=>setTimeout(r,120000))]);
    if(stopResolve){status('La captura terminó, pero el servidor sigue procesando. Revisa el texto exportado antes de cerrar.',true);stopResolve=null;}
    else status('Captura detenida. Puedes continuar o exportar la sesión.');
    try{ws.close()}catch{}
  }
  controls(false);stopping=false;
}
$('start').onclick=start;$('stop').onclick=stop;
$('warmup').onclick=async()=>{$('warmup').disabled=true;status('Preparando Whisper local. La primera descarga puede tardar varios minutos.');try{const r=await fetch('/api/warmup',{method:'POST'}),data=await r.json();if(!r.ok)throw Error(data.detail||'No se pudo preparar el modelo.');status('Whisper local preparado. Puedes iniciar la captura.')}catch(e){status(e.message,true)}finally{providerHint()}};
$('view').onchange=()=>channel.postMessage({type:'view',view:$('view').value});
function addTranscript(ev){const p=document.createElement('p'),small=document.createElement('small');small.textContent=ev.speaker+' · '+(ev.method||'')+'\n';p.append(small,document.createTextNode(ev.text));$('transcript').append(p);while($('transcript').children.length>150)$('transcript').firstChild.remove();$('transcript').scrollTop=$('transcript').scrollHeight;}
let viewer,retry;
function connectViewer(){viewer=new WebSocket(wsURL('/ws/view/'+sid));viewer.onmessage=e=>{const m=JSON.parse(e.data);if(m.type==='snapshot'){$('transcript').replaceChildren();m.events.forEach(addTranscript)}if(m.type==='event')addTranscript(m.event);if(m.type==='reset'){$('transcript').replaceChildren();$('partial').textContent=''}};viewer.onclose=()=>{retry=setTimeout(connectViewer,1500)}}connectViewer();
setInterval(()=>{if(viewer?.readyState===WebSocket.OPEN)viewer.send('ping')},20000);
$('sendText').onclick=async()=>{const text=$('manual').value.trim();if(!text)return;try{const r=await fetch('/api/sessions/'+sid+'/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});if(!r.ok)throw Error('No se pudo enviar el fragmento');$('manual').value='';status('Fragmento incorporado.')}catch(e){status(e.message,true)}};
$('reset').onclick=async()=>{try{const r=await fetch('/api/sessions/'+sid,{method:'DELETE'});if(!r.ok)throw Error('No se pudo vaciar la sesión');status('Sesión vacía.')}catch(e){status(e.message,true)}};
$('download').onclick=async()=>{const response=await fetch('/api/sessions/'+sid+'/events');if(!response.ok)return status('No se pudo exportar.',true);const data=await response.json();const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=sid+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),500)};
window.addEventListener('beforeunload',()=>{for(const s of streams)for(const t of s.getTracks())t.stop();socket?.close();viewer?.close();channel.close()});
