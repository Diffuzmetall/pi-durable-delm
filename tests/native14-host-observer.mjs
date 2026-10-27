// Read-only witness admitted by the REAL Native --extension registry loader.
import {appendFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {defineExtension,hook,GenerationTask} from '@earendil-works/pi-durable';
export default async function observeActualRegistry(registry) {
 const log=value=>appendFileSync(process.env.DELM_NATIVE14_OBSERVER_LOG,JSON.stringify(value)+'\n');
 const snapshot=registry.snapshot();
 const controller=snapshot.extension('hindsight')?.[Symbol.for('pi.durable.hindsight.controller')];
 if(typeof controller?.admit!=='function'||typeof controller?.submit!=='function')throw Error('Real host admission controller absent; fixture will not provide one');
 const {ContextState}=await import(pathToFileURL(process.env.PI_DURABLE_EXTENSION_ROOT+'/packages/hindsight/src/extension.mjs').href);
 registry.install(defineExtension({name:'native14-readonly-fixture-witness',hooks:[hook(GenerationTask,{
  async beforeRequest(_request,api,context){
   const state=await api.snapshot(ContextState,api.conversationId,context);
   const admittedRequests=Object.keys(state?.admissions??{});
   if(!admittedRequests.length)throw Error('Real Native admission missing; observer refuses to fake it');
   log({event:'real_admission_observed_through_sdk',pid:process.pid,conversationId:api.conversationId,admittedRequests,
    memoryEnabled:false,policyOrRequestChanged:false});
  },
 })]}));
 log({event:'actual_registry_adapter_loaded',pid:process.pid,realHindsightControllerPresent:true,
  tools:snapshot.tools().map(({tool})=>tool.name),extensions:snapshot.installed().map(e=>e.name),
  readOnlyObserverAdded:true,registryOrPolicyReplaced:false});
 return registry;
}
