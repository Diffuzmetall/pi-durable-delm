// Private DeLM control inside the existing Native owner. No Harness/storage/model runtime is created.
import { createServer } from 'node:net';
import { lstat, realpath, chmod } from 'node:fs/promises';
import { realpathSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { defineDoc, ROOT_CONVERSATION_ID } from '@earendil-works/pi-durable';
import { createNativeInput } from '../../skills/delm/Tools/NativeInput.mjs';
import { DelmWaitDoc, DELM_BUILD } from './index.js';

export const NATIVE14_PROTOCOL = 'delm.native14.control.v1';
export const NATIVE14_BUILD = `${DELM_BUILD}+native14-owner-v1`;
export const NATIVE14_OWNER = Symbol.for('delm.native14.owner');
export const Native14Binding = defineDoc({ kind:'delm.native14.binding', version:1, scope:'conversation',
  history:'latest', fork:'initial', checkpointWhen:()=>false,
  initial:()=>({instanceId:null,binding:null,stopped:false}) });
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = (code,message) => { throw Object.assign(Error(message),{code}); };

export function prepareNative14Owner(controller, {run,actor,workspace,controlSocket}) {
  if (!isAbsolute(controlSocket)) fail('INVALID_REQUEST','DeLM controlSocket must be absolute');
  if (typeof controller.bind !== 'function' || typeof controller.close !== 'function')
    fail('NOT_READY','Current Native trusted owner bind/close capability required');
  const options={run:realpathSync(run),actor,workspace,controlSocket:resolve(controlSocket)};
  const previous=controller[NATIVE14_OWNER];
  if(previous) {
    if(Object.keys(options).some(key=>previous.options[key]!==options[key]))
      fail('SCOPE_MISMATCH','DeLM current owner cannot be rebound to another run/actor/control endpoint');
  }
  let releaseReady;
  const state=previous??{options,owner:null,root:null,identity:null,tool:null,server:null,clients:new Set(),
    closed:false,failure:null,ready:new Promise(resolve=>{releaseReady=resolve;})};
  if(!previous) Object.defineProperty(controller,NATIVE14_OWNER,{value:state});
  state.wait=async(context)=>{
    const signal=context.abortSignal;
    signal?.throwIfAborted();
    let onAbort;
    try {
      await Promise.race([state.ready,new Promise((_,reject)=>{
        onAbort=()=>reject(signal.reason); signal?.addEventListener('abort',onAbort,{once:true});
      })]);
    } finally { if(onAbort) signal?.removeEventListener('abort',onAbort); }
    if(state.closed || state.failure || !state.owner) fail('NOT_READY','DeLM owner/control is unavailable');
  };
  state.active=async(context,allowStopped=false,checkWorkspace=true)=>{
    await state.wait(context);
    if(checkWorkspace) {
      const agent=await state.root.agent(context);
      if(!agent.cwd || realpathSync(agent.cwd)!==workspace) fail('SCOPE_MISMATCH','DeLM effective workspace changed');
    }
    const doc=await state.owner.session.snapshot(Native14Binding,ROOT_CONVERSATION_ID,context);
    if(!doc?.binding || Object.keys(doc.binding).some(key=>doc.binding[key]!==state.identity[key]))
      fail('SCOPE_MISMATCH','DeLM native binding changed');
    if(doc.stopped && !allowStopped) fail('STOPPED','DeLM actor is stopped; resume explicitly');
    return doc;
  };
  const identityCheck=expected=>{
    if(!record(expected) || Object.keys(state.identity).some(key=>expected[key]!==state.identity[key]))
      fail('SCOPE_MISMATCH','DeLM exact run/actor/session/instance identity mismatch');
  };
  const handle=async request=>{
    if(!record(request) || typeof request.id!=='string' || !request.id.trim() || request.id.length>256 ||
      !['identity','input','status','stop','resume'].includes(request.method)) fail('INVALID_REQUEST','Invalid DeLM control request');
    const context=state.owner.context;
    await state.wait(context);
    if(request.method==='identity') {
      const doc=await state.active(context,true,false);
      return {identity:state.identity,stopped:doc.stopped,build:NATIVE14_BUILD};
    }
    identityCheck(request.identity);
    if(request.method==='input') {
      if(request.type!=='input') fail('INVALID_REQUEST','Only approved input type is accepted');
      await state.active(context);
      const input=createNativeInput({host:state.owner.session,conversation:state.root,
        session:state.identity.sessionPath,expectedSession:state.identity.sessionPath,
        admitInput:async(conversation,id,ctx)=>{
          await state.active(ctx); await controller.admit(conversation,id,ctx); await state.active(ctx);
        }});
      return input(request,context);
    }
    await state.active(context,true,request.method==='resume');
    if(request.method==='status') {
      const result=await state.tool.execute({action:'status'},{conversationId:ROOT_CONVERSATION_ID,
        commit:(fn,c)=>state.owner.session.commit(fn,c)},context);
      const doc=await state.owner.session.snapshot(Native14Binding,ROOT_CONVERSATION_ID,context);
      return {identity:state.identity,stopped:doc.stopped,waits:result.structuredOutput.result};
    }
    if(request.method==='resume') {
      await state.owner.session.commit(async tx=>{(await tx.doc(Native14Binding,ROOT_CONVERSATION_ID)).stopped=false;},context);
      return {identity:state.identity,resumed:true};
    }
    await state.owner.session.commit(async tx=>{(await tx.doc(Native14Binding,ROOT_CONVERSATION_ID)).stopped=true;},context);
    const doc=await state.owner.session.snapshot(DelmWaitDoc,ROOT_CONVERSATION_ID,context);
    const waits=[];
    for(const entry of Object.values(doc?.waits??{})) {
      if(!['waiting','failed'].includes(entry.state)) continue;
      const id=entry.watcherTaskId??entry.taskId;
      await state.owner.session.abortTask(id,context);
      await state.owner.session.waitForTask(id,context);
      waits.push({id:entry.id,aborted:true});
    }
    await state.root.abort(context); await state.root.waitForIdle(context);
    return {identity:state.identity,stopped:true,waits};
  };
  state.handle=handle;
  if(previous) return state;
  const originalBind=controller.bind;
  controller.bind=async function(host) {
    const result=await originalBind.call(this,host);
    state.owner=host;
    try {
      state.root=await host.session.conversation(ROOT_CONVERSATION_ID,host.context);
      if(!state.root) fail('NOT_READY','Native root is missing');
      const sessionPath=await realpath(join(host.directory,'session.sqlite'));
      const binding={run:options.run,actor,workspace,sessionPath,sessionId:basename(dirname(sessionPath)),conversationId:ROOT_CONVERSATION_ID};
      const instanceId=await host.session.commit(async tx=>{
        const doc=await tx.doc(Native14Binding,ROOT_CONVERSATION_ID);
        if(doc.binding && Object.keys(binding).some(key=>doc.binding[key]!==binding[key]))
          fail('SCOPE_MISMATCH','Native session already belongs to a different DeLM binding');
        doc.binding=binding; doc.instanceId??=randomUUID(); return doc.instanceId;
      },host.context);
      state.identity={protocol:NATIVE14_PROTOCOL,sdkVersion:'1.4.0',...binding,instanceId};
      const parent=await lstat(dirname(options.controlSocket));
      if(!parent.isDirectory() || parent.isSymbolicLink() || parent.uid!==process.getuid?.() || (parent.mode&0o077))
        fail('SCOPE_MISMATCH','DeLM control parent must be a private user-owned directory (0700)');
      const server=createServer(socket=>{
        state.clients.add(socket); socket.on('error',()=>socket.destroy());
        socket.once('close',()=>state.clients.delete(socket));
        let buffer=Buffer.alloc(0),used=false;
        socket.on('data',chunk=>{
          if(used) {socket.destroy();return;}
          buffer=Buffer.concat([buffer,chunk]);
          if(buffer.length>1048576) {socket.destroy();return;}
          const end=buffer.indexOf(10); if(end<0) return;
          used=true;
          void (async()=>{
            let request;
            try {
              if(buffer.subarray(end+1).toString('utf8').trim()) fail('INVALID_REQUEST','One request per connection');
              request=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,end)));
              const result=await state.handle(request);
              socket.end(JSON.stringify({id:request.id,ok:true,result})+'\n');
            } catch(error) {
              const code=['INVALID_REQUEST','SCOPE_MISMATCH','STOPPED','NOT_READY'].includes(error.code)?error.code:'CONTROL_ERROR';
              socket.end(JSON.stringify({id:typeof request?.id==='string'?request.id:null,ok:false,
                error:{code,message:String(error.message??'DeLM control failed').slice(0,256)}})+'\n');
            }
          })();
        });
      });
      const listening=once(server,'listening'); server.listen(options.controlSocket); await listening;
      try {await chmod(options.controlSocket,0o600);}
      catch(error) {await new Promise(resolve=>server.close(resolve));throw error;}
      server.on('error',()=>{state.failure=Error('DeLM control listener failed');});
      state.server=server;
    } catch(error) {
      // A DeLM control failure must never disable the existing owner's successful Hindsight bind.
      state.failure=error; console.error('DeLM current Native control unavailable; approved DeLM input remains disabled');
    } finally {releaseReady();}
    return result;
  };
  const originalClose=controller.close;
  controller.close=async function(...args) {
    state.closed=true; releaseReady();
    try {
      for(const socket of state.clients) socket.destroy();
      if(state.server) await new Promise((resolve,reject)=>state.server.close(error=>error?reject(error):resolve()));
    } finally {await originalClose.apply(this,args);}
  };
  return state;
}
