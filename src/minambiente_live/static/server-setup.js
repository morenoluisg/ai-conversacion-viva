'use strict';
const $=id=>document.getElementById(id),connection=window.ConversationConnection;
const query=new URLSearchParams(location.search),candidate=query.get('session');
const session=connection.validSession(candidate)?candidate:localStorage.getItem('minambiente-session')||('charla-'+crypto.randomUUID().slice(0,8));
$('serverUrl').value=location.origin;$('sessionId').value=session;
function prepare(){
 try{const origin=connection.serverOrigin($('serverUrl').value),sid=$('sessionId').value.trim(),links=connection.links(origin,sid);
  $('adminLink').href=links.admin;$('captureLink').href=links.capture;$('visualLink').href=links.visual;$('shareCapture').value=links.capture;$('sessionLinks').hidden=false;
  const remoteHTTP=origin.startsWith('http:')&&!/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(origin);
  $('setupStatus').textContent=remoteHTTP?'Enlaces preparados. Para capturar audio desde otro equipo debes configurar HTTPS en este servidor.':origin===location.origin?'Enlaces preparados para este servidor. Comparte el de captura con el operador.':'Enlaces preparados. Abre el panel del servidor de destino para comprobar que esté disponible; todavía no se ha enviado audio.';
  $('setupStatus').classList.toggle('error',remoteHTTP);
  if(origin===location.origin)localStorage.setItem('minambiente-session',sid);
 }catch(e){$('sessionLinks').hidden=true;$('setupStatus').textContent=e.message;$('setupStatus').classList.add('error')}
}
$('connectForm').onsubmit=e=>{e.preventDefault();prepare()};
$('copyLink').onclick=async()=>{try{await navigator.clipboard.writeText($('shareCapture').value);$('setupStatus').textContent='Enlace copiado.'}catch{$('shareCapture').select();$('setupStatus').textContent='Selecciona y copia el enlace.'}};
prepare();
