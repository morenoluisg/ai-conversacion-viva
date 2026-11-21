import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
const test=fs.readFileSync('tests/test_visual.mjs','utf8');
const factory=test.slice(test.indexOf('function boot('),test.indexOf('\nfor(const query'));
for(const entry of ['docs/index.html','docs/demo/Conversacion_Viva.html']){
 const html=fs.readFileSync(entry,'utf8');
 for(const match of html.matchAll(/(?:src|href)="([^"]+)"/g)){
  if(match[1].startsWith('http')||match[1].startsWith('#'))continue;
  assert.ok(!match[1].startsWith('/'),'Pages assets must be relative');
  assert.ok(fs.existsSync(path.resolve(path.dirname(entry),match[1])),match[1]);
 }
 const mappedFs={readFileSync:(file,...args)=>file==='src/minambiente_live/static/visual.html'?html:fs.readFileSync(file,...args)};
 const boot=new Function('fs','vm','return ('+factory.trim()+')')(mappedFs,vm);
 const sandbox=boot('?live=1');
 assert.equal(vm.runInContext('LIVE_MODE',sandbox),false);
 sandbox.appBranding={app_name:'Conversación viva',organization:'Ejemplo',description:'Conversación',center_top:'DIÁLOGO',center_bottom:'AMBIENTAL',panel_heading:'Ahora conversamos sobre',accent_color:'#287a38'};
 sandbox.setBranding=value=>sandbox.appBranding={...sandbox.appBranding,...value};
 const callbacks=[];sandbox.setTimeout=fn=>callbacks.push(fn);
 const create=sandbox.document.createElement,forms=[],dialogs=[];
 sandbox.document.createElement=tag=>{const element=create();if(tag==='form')forms.push(element);if(tag==='dialog'){element.showModal=()=>element.open=true;element.close=()=>element.open=false;dialogs.push(element)}return element};
 vm.runInContext(fs.readFileSync('docs/demo-assets/demo.js','utf8'),sandbox);
 sandbox.document.getElementById('demoSettings').onclick();
 assert.equal(dialogs[0].open,true);
 sandbox.document.getElementById('demoBrand_app_name').value='Encuentro de educación';
 forms[0].onsubmit({preventDefault(){}});
 assert.equal(sandbox.appBranding.app_name,'Encuentro de educación');
 assert.equal(dialogs[0].open,false);
 assert.equal(vm.runInContext('events.length',sandbox),5);
 vm.runInContext('step()',sandbox);
 assert.equal(vm.runInContext('playing',sandbox),true);
 assert.equal(vm.runInContext('events.length',sandbox),6);
 callbacks.splice(0).forEach(fn=>fn());
 assert.equal(vm.runInContext('events.length',sandbox),6);
 assert.equal(vm.runInContext('playing',sandbox),true);
 for(const lens of ['agenda','manual','automatic']){
  vm.runInContext('switchLens('+JSON.stringify(lens)+')',sandbox);
  for(const view of ['radial','sunburst','flow','particles','field','constellation','stream'])vm.runInContext('setView('+JSON.stringify(view)+');render(performance.now())',sandbox);
  assert.equal(vm.runInContext('events.length',sandbox),6);
 }
 vm.runInContext('toggleControls();toggleTextPanel();setTheme("dark")',sandbox);
 assert.equal(vm.runInContext('textPanelVisible()',sandbox),true);
 assert.equal(sandbox.document.documentElement.dataset.theme,'dark');
 sandbox.document.getElementById('text').value='Agua y bosques';sandbox.document.getElementById('add').onclick();
 callbacks.splice(0).forEach(fn=>fn());
 assert.equal(vm.runInContext('events.length',sandbox),7);
 assert.equal(vm.runInContext('playing',sandbox),false);
 sandbox.document.getElementById('reset').onclick();
 assert.equal(vm.runInContext('events.length',sandbox),1);
 callbacks.splice(0).forEach(fn=>fn());
 assert.equal(vm.runInContext('events.length',sandbox),1);
 assert.equal(vm.runInContext('playing',sandbox),true);
 console.log(entry+': siete vistas, tres lecturas simuladas, temas asíncronos, reproducción, reinicio, K, fondo y recursos relativos: OK');
}
