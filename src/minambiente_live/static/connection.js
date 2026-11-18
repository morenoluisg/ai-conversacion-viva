'use strict';
window.ConversationConnection={
 validSession(value){return typeof value==='string'&&/^[A-Za-z0-9_-]{1,64}$/.test(value)},
 serverOrigin(raw){
  let value=String(raw).trim();if(!value)throw Error('Escribe la dirección del servidor.');
  if(!/^https?:\/\//i.test(value)){const local=/^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?\/?$/i.test(value);value=(local?'http://':'https://')+value}
  let url;try{url=new URL(value)}catch{throw Error('La dirección del servidor no es válida.')}
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Usa solo la dirección del servidor, sin rutas, claves ni parámetros.');
  return url.origin;
 },
 links(origin,session){
  if(!this.validSession(session))throw Error('El código de sesión no es válido.');
  const base=this.serverOrigin(origin),query=new URLSearchParams({session});
  return {admin:base+'/admin?'+query,capture:base+'/captura?'+query,visual:base+'/visual?'+new URLSearchParams({session,live:'1',lens:'agenda'})};
 }
};
