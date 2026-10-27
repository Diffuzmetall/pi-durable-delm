// Measurement only: use the ACTUAL SDK1.4 system-delta replay; assertions belong to the Python harness.
import {appendFileSync,readFileSync,writeFileSync} from 'node:fs';
import {defineExtension,GenerationTask,hook} from '@earendil-works/pi-durable';
import {getCurrentSystemPrompt,getCurrentTools} from '@earendil-works/pi-ai/utils/transcript';
export default function measure(registry){
 const p=JSON.parse(readFileSync(process.env.N14_ACCEPT_PLAN,'utf8'));
 registry.install(defineExtension({name:'n14-postremove-prompt-measure',hooks:[hook(GenerationTask,{beforeRequest(request){
  let result;
  try{
   const system=request.messages.filter(m=>m.role==='system');
   const current=getCurrentSystemPrompt(request.messages);
   const tools=getCurrentTools(request.messages).map(t=>t.name);
   writeFileSync(p.privateSystem,JSON.stringify({system,current,tools},null,2));
   result={event:'postremove_current_prompt_measured',systemMessages:system.length,
    historicalDelmSkill:JSON.stringify(system).includes('<name>delm</name>'),
    currentDelmSkill:current.includes('<name>delm</name>'),currentDelmWaitTool:tools.includes('delm_wait'),
    currentTools:tools,systemDeltaSections:system.map(m=>Object.fromEntries(Object.entries(m.sections??{}).map(([key,value])=>[key,value===null?null:{length:value.length,delm:value.includes('<name>delm</name>')}]))),
    sdkReplay:'@earendil-works/pi-ai/utils/transcript getCurrentSystemPrompt/getCurrentTools; installed1.4.0'};
  }catch(error){result={event:'measurement_error',error:String(error)};}
  // Native hooks report errors softly. NEVER infer absence from a missing record/successful assistant reply.
  appendFileSync(p.observations,JSON.stringify(result)+'\n');
 }})]}));return registry;
}
