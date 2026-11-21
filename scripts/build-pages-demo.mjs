import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const branding={app_name:'Conversación viva',organization:'MinAmbiente · Laboratorio de ideas',description:'Una conversación que construimos juntos',center_top:'DIÁLOGO',center_bottom:'AMBIENTAL',panel_heading:'Ahora conversamos sobre',accent_color:'#287a38'};
const source=read('src/minambiente_live/static/visual.html');
fs.mkdirSync(path.join(root,'docs/demo-assets'),{recursive:true});
for(const name of ['branding.js','branding.css'])fs.copyFileSync(path.join(root,'src/minambiente_live/static',name),path.join(root,'docs/demo-assets',name));
for(const [destination,assets] of [['docs/index.html','./demo-assets/'],['docs/demo/Conversacion_Viva.html','../demo-assets/']]){
 let html=source.replace("const LIVE_MODE=new URLSearchParams(location.search).get('live')==='1';",'const LIVE_MODE=false; // Public demo: no server or API credentials.');
 html=html.replace('<script>',`<link rel="stylesheet" href="${assets}branding.css"><link rel="stylesheet" href="${assets}demo.css"><script id="appBranding" type="application/json">${JSON.stringify(branding)}</script><script src="${assets}branding.js"></script><script>`);
 html=html.replace('<footer class="controls">','<footer class="controls"><span class="demo-note">Demo interactiva · Texto y temas simulados · Sin APIs de pago</span><button id="demoSettings">Identidad y presentación</button><label for="demoTheme">Fondo</label><select id="demoTheme"><option value="light">Claro</option><option value="dark">Oscuro</option></select><span id="demoAnalysis" role="status"></span>');
 html=html.replace('Agenda SINA CONECTA</option>','Agenda de ejemplo</option>').replace('DeepSeek autónomo</option>','Temas automáticos · simulados</option>');
 html=html.replaceAll('EN VIVO ·','DEMO ·').replaceAll('DEEPSEEK AUTÓNOMO','TEMAS AUTOMÁTICOS SIMULADOS').replaceAll('DEEPSEEK NO DISPONIBLE','ANÁLISIS SIMULADO NO DISPONIBLE');
 html=html.replace("demo:!LIVE_MODE,method:","demo:!LIVE_MODE,identity:window.appBranding,method:");
 html=html.replace('ingest({text:e.results[i][0].transcript', 'window.demoIngest({text:e.results[i][0].transcript');
 html=html.replace('</html>',`<script src="${assets}demo.js"></script></html>`);
 fs.writeFileSync(path.join(root,destination),html);
}
console.log('Demo de Pages actualizada desde visual.html: dos entradas y recursos relativos.');
