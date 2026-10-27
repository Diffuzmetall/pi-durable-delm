// TEST-ONLY real Native owner policy. Installed before DeLM binding, using the existing owner's registry.
import {defineFacet,defineService} from '@earendil-works/chord';
import {BACKGROUND_CONTEXT as context} from '@earendil-works/chord/context';
import {defineExtension,hook,ToolTask} from '@earendil-works/pi-durable';
import {DurableSession} from '@earendil-works/pi-coding-agent/experimental/plugin';
const Policy = defineService('fixture.owner-policy');
export default defineFacet({id:'fixture.existing-owner-policy',setup(env){
  const capability=env.use(DurableSession);
  let enabled=false,blocked=0,owner;
  env.provide(Policy,{
    async enable(){enabled=true;return {enabled};},
    async stats(){return {enabled,blocked,fixtureVersion:'owner-policy-v1'};}
  });
  env.onActivate(async()=>{
    owner=await capability.get(context);
    owner.registry.install(defineExtension({name:'fixture-existing-policy',hooks:[hook(ToolTask,{
      beforeTool:call=>{if(enabled&&call.name==='delm_wait'){blocked++;return {block:'FIXTURE_EXISTING_OWNER_POLICY_DENIED'};}}
    })]}));
  });
  // The fixture owner's policy lives for this registry's lifetime; reload installs its replacement by name.
  // Do not let a retiring test facet uninstall the replacement generation's policy.
}});
