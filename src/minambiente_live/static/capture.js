'use strict';
const $=id=>document.getElementById(id),query=new URLSearchParams(location.search),sid=query.get('session'),valid=window.ConversationConnection.validSession(sid);
$('serverAddress').textContent=location.origin;$('sessionName').textContent=valid?sid:'Falta un código de sesión válido';
$('changeServer').href='/servidor'+(valid?'?'+new URLSearchParams({session:sid}):'');
$('openVisual').href=valid?'/visual?'+new URLSearchParams({session:sid,live:'1',lens:'agenda'}):'/servidor';
let poll,client;
function transcript(text){const p=document.createElement('p');p.textContent=text;$('captureTranscript').append(p);while($('captureTranscript').children.length>80)$('captureTranscript').firstChild.remove()}
async function check(){
 try{const r=await fetch('/api/sessions/'+sid+'/status');if(!r.ok)throw Error('El servidor no respondió');const data=await r.json();
  $('connectionStatus').textContent=(data.capturing?'Hay una captura activa en esta sesión.':'Servidor disponible para esta sesión.')+' · '+data.fragments+' fragmentos confirmados';
  $('start').disabled=!window.isSecureContext||(!client?.isCapturing()&&data.capturing)||!!client?.isCapturing();
 }catch{$('connectionStatus').textContent='No se puede contactar con el servidor. Revisa la conexión.';if(!client?.isCapturing())$('start').disabled=true}
 poll=setTimeout(check,4000);
}
if(valid){client=window.initAudioCapture({session:sid,onTranscript:transcript});check()}else{$('status').textContent='Abre el enlace de captura de una sesión o usa Cambiar servidor o sesión.';$('status').classList.add('error');$('start').disabled=true;$('warmup').disabled=true}
if(!window.isSecureContext){$('connectionStatus').textContent='La captura requiere HTTPS. localhost solo funciona en el propio equipo.';$('connectionStatus').classList.add('error')}
window.addEventListener('beforeunload',()=>clearTimeout(poll));
