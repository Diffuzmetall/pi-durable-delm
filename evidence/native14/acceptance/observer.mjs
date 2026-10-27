// TEST instrumentation on the genuine registry: observe skills/admission; never replace policy decisions.
import {appendFileSync,existsSync,readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {defineExtension,GenerationTask,hook} from '@earendil-works/pi-durable';
export default function observe(registry){
 const config=JSON.parse(readFileSync(process.env.N14_ACCEPT_PLAN,'utf8'));
 const log=v=>appendFileSync(config.observations,JSON.stringify(v)+'\n');
 const controller=registry.snapshot().extension('hindsight')?.[Symbol.for('pi.durable.hindsight.controller')];
 if(typeof controller?.admit!=='function')throw Error('Actual admission missing; test will not fabricate it');
 const admit=controller.admit.bind(controller);
 controller.admit=async(...args)=>{
  const value=await admit(...args); // The REAL policy and commit always run, with the original arguments.
  if(args[1]===config.holdRequestId){
   writeFileSync(config.admitted,'real admission completed');
   const end=Date.now()+20000;
   while(!existsSync(config.release)){
    if(Date.now()>end)throw Error('TEST scheduling gate expired after actual admission');
    await new Promise(r=>setTimeout(r,10));
   }
  }
  return value;
 };
 registry.install(defineExtension({name:'n14-accept-readonly-prompt-witness',hooks:[hook(GenerationTask,{
  beforeRequest(request){
   const system=request.messages.filter(m=>m.role==='system').map(m=>JSON.stringify(m)).join('\n');
   const location=config.skillLocations.find(p=>system.includes(p));
   const hasSkill=system.includes('<name>delm</name>');
   if(config.expectSkill&&(!hasSkill||!location))throw Error('Actual installed Native prompt did not discover packaged DeLM skill');
   if(!config.expectSkill&&hasSkill)throw Error('Removed DeLM skill still advertised by Native');
   const history=JSON.stringify(request.messages.filter(m=>m.role!=='system'));
   if(config.draft&&history.includes(config.draft))throw Error('Unsent editor draft entered actual model history');
   log({event:'actual_native_skill_prompt',skillPresent:hasSkill,location,draftAbsentModelHistory:true,systemSha256:createHash('sha256').update(system).digest('hex')});
  },
 })]}));
 return registry;
}
