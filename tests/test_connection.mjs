import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const context={window:{},URL,URLSearchParams};vm.createContext(context);vm.runInContext(fs.readFileSync('src/minambiente_live/static/connection.js','utf8'),context);
const c=context.window.ConversationConnection;
assert.equal(c.serverOrigin('127.0.0.1:8765'),'http://127.0.0.1:8765');
assert.equal(c.serverOrigin('conversacion.example'),'https://conversacion.example');
assert.equal(c.links('https://conversacion.example','charla-1').capture,'https://conversacion.example/captura?session=charla-1');
for(const bad of ['https://user:pass@example.com','https://example.com/path','https://example.com/?token=secret','javascript:alert(1)','https://example.com/#test'])assert.throws(()=>c.serverOrigin(bad));
for(const bad of ['','../admin','sesión','a'.repeat(65)])assert.equal(c.validSession(bad),false);
// Both pages must expose every control required by the shared audio client.
const shared=fs.readFileSync('src/minambiente_live/static/capture-audio.js','utf8');
const ids=[...shared.matchAll(/\$\('([A-Za-z]+)'\)/g)].map(m=>m[1]).filter(id=>!['generateReport','reset'].includes(id));
for(const page of ['operator.html','capture.html']){const html=fs.readFileSync('src/minambiente_live/static/'+page,'utf8');for(const id of ids)assert.ok(html.includes('id="'+id+'"'),page+' missing '+id)}
console.log('Conexiones, enlaces por sesión y contrato de audio compartido: OK');
