// Repair measurement only. Never throw a soft SDK hook as a substitute for a harness assertion.
import {appendFileSync,readFileSync,writeFileSync} from 'node:fs';
import {defineExtension,GenerationTask,hook} from '@earendil-works/pi-durable';
export default function measure(registry){
 const p=JSON.parse(readFileSync(process.env.N14_ACCEPT_PLAN,'utf8'));
 registry.install(defineExtension({name:'n14-postremove-prompt-measure',hooks:[hook(GenerationTask,{beforeRequest(request){
  const system=request.messages.flatMap((m,index)=>m.role==='system'?[{index,content:m.content,keys:Object.keys(m)}]:[]);
  writeFileSync(p.privateSystem,JSON.stringify(system,null,2));
  appendFileSync(p.observations,JSON.stringify({event:'postremove_prompt_measured',system:system.map(m=>{
   const content=typeof m.content==='string'?m.content:JSON.stringify(m.content);
   return {index:m.index,keys:m.keys,length:content.length,delm:content.includes('<name>delm</name>'),
    snippets:[...content.matchAll(/.{0,80}<name>delm<\/name>.{0,250}/g)].map(v=>v[0]),
    locations:[...content.matchAll(/<location>[^<]+<\/location>/g)].map(v=>v[0])};
  })})+'\n');
 }})]}));return registry;
}
