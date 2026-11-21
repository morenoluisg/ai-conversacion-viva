'use strict';
window.appBranding=JSON.parse(document.getElementById('appBranding').textContent);
window.setBranding=function(branding){
 window.appBranding={...window.appBranding,...branding};
 const current=window.appBranding;
 document.title=current.app_name;
 for(const element of document.querySelectorAll('[data-brand]'))element.textContent=current[element.dataset.brand]||'';
 document.documentElement.style.setProperty('--brand-accent',current.accent_color);
 const rgb=[1,3,5].map(i=>parseInt(current.accent_color.slice(i,i+2),16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const light=rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722;
 document.documentElement.style.setProperty('--brand-ink',light>.179?'#102921':'#ffffff');
 const green=document.documentElement.dataset.theme==='dark'?'#96e5a5':current.accent_color;
 document.documentElement.style.setProperty('--green',green);
};
window.setBranding(window.appBranding);
