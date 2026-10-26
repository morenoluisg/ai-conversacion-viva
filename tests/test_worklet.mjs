import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const code=fs.readFileSync(new URL('../src/minambiente_live/static/audio-worklet.js',import.meta.url),'utf8');
for(const rate of [44100,48000]){
 let Processor;const output=[];const env={sampleRate:rate,Int16Array,Math,AudioWorkletProcessor:class {constructor(){this.port={postMessage:m=>{if(m.pcm)output.push(new Int16Array(m.pcm))}}}},registerProcessor:(name,p)=>{Processor=p}};
 vm.createContext(env);vm.runInContext(code,env);const capture=new Processor();
 // Un segundo completo a amplitud constante: debe convertirse en 16000 muestras.
 for(let start=0;start<rate;start+=128){const n=Math.min(128,rate-start);capture.process([[new Float32Array(n).fill(.25)]],[[new Float32Array(n)]]);}
 capture.flush();const samples=output.reduce((sum,a)=>sum+a.length,0);assert.equal(samples,16000,'sample count '+rate);
 assert.ok(output.every(a=>a.every(v=>Math.abs(v-8192)<=1)),'PCM amplitude '+rate);
}
console.log('Resampling 44.1/48 kHz, PCM16 amplitude and flush pass.');
