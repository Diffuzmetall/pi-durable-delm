// TEST ONLY: replace ModelRuntime.create, never Native main/loader/registry/admission/storage.
import {appendFileSync,readFileSync} from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {dirname,join} from 'node:path';
import {createHash} from 'node:crypto';
const file=process.env.DELM_NATIVE14_PLAN;
if(file && process.argv[1]?.endsWith('/experimental/durable/main.ts')) {
 const plan=JSON.parse(readFileSync(file,'utf8'));
 await import(pathToFileURL(plan.globalRuntime).href);
 const {createModels}=await import('@earendil-works/pi-ai/models');
 const {fauxProvider,fauxAssistantMessage,fauxToolCall}=await import('@earendil-works/pi-ai/providers/faux');
 const {ModelRuntime}=await import(pathToFileURL(plan.modelRuntime).href);
 const log=record=>appendFileSync(plan.modelLog,JSON.stringify(record)+'\n');
 const modules={};
 for(const name of ['pi-durable','pi-ai','chord']) {
  const url=import.meta.resolve('@earendil-works/'+name);let p=dirname(fileURLToPath(url));
  while(!readable(join(p,'package.json')))p=dirname(p);
  const pkg=JSON.parse(readFileSync(join(p,'package.json'),'utf8'));
  if(pkg.version!=='1.4.0')throw Error('Fixture requires actual published SDK1.4: '+name);
  modules[name]={url,manifest:join(p,'package.json'),version:pkg.version,
   entrySha256:createHash('sha256').update(readFileSync(fileURLToPath(url))).digest('hex'),
   manifestSha256:createHash('sha256').update(readFileSync(join(p,'package.json'))).digest('hex')};
 }
 const faux=fauxProvider({tokensPerSecond:10000});
 const counts=new Map();
 faux.setResponses(Array.from({length:64},()=>transcript=>{
  const user=transcript.messages.findLast(m=>m.role==='user');
  const text=typeof user?.content==='string'?user.content:(user?.content??[]).filter(b=>b.type==='text').map(b=>b.text).join('\n');
  const marker=Object.keys(plan.routes).find(k=>text.includes(k));
  if(!marker)throw Error('Unplanned model request refused by deterministic MODEL fixture');
  const index=counts.get(marker)??0;counts.set(marker,index+1);
  const action=plan.routes[marker][index];if(!action)throw Error('Unexpected duplicate model request for '+marker);
  if(action.expectToolText&&!JSON.stringify(transcript.messages.at(-1)).includes(action.expectToolText))throw Error('Actual Native tool result missing expected fixture text');
  const declared=transcript.messages.flatMap(m=>m.toolsAdded??[]).map(t=>t.name);
  if(action.tool&&!declared.includes(action.tool))throw Error('MODEL fixture requested a tool not advertised by actual Native');
  log({event:'model_request',pid:process.pid,marker,index,tools:declared});
  return action.tool?fauxAssistantMessage(fauxToolCall(action.tool,action.arguments),{stopReason:'toolUse'}):fauxAssistantMessage(action.text);
 }));
 const models=createModels();models.setProvider(faux.provider);
 Object.assign(models,{getAvailableSnapshot:()=>faux.models,hasConfiguredAuth:()=>true});
 ModelRuntime.create=async()=>models;
 log({event:'model_boundary_installed',pid:process.pid,nodeVersion:process.version,main:process.argv[1],modules,substitution:'ModelRuntime.create ONLY'});
}
function readable(file){try{readFileSync(file);return true;}catch{return false;}}
