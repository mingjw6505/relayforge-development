import {App} from '@modelcontextprotocol/ext-apps';
import {PanelPoller,terminal} from './poller.mjs';
import {cardView} from './view.mjs';

const app=new App({name:'RelayForge Development Progress',version:__PLUGIN_VERSION__},
  {availableDisplayModes:['inline']},{autoResize:true});
const el=id=>document.getElementById(id);
const stepNames={pending:'待处理',active:'当前',done:'完成',blocked:'受阻',skipped:'跳过'};
let latest;
function line(...values) {
  const row=document.createElement('li');
  for(const value of values){const text=document.createElement('span');text.textContent=value;row.append(text);}
  return row;
}
function time(value) {const date=new Date(value);return Number.isNaN(date.getTime())?'—':date.toLocaleTimeString([],{hour12:false});}
function stale() {
  el('stale').hidden=!latest||terminal(latest.status)||Date.now()-Date.parse(latest.updated_at)<=90000;
}
function render(snapshot) {
  latest=snapshot;
  const view=cardView(snapshot);
  el('empty').hidden=true;el('task').hidden=false;
  document.body.dataset.status=snapshot.status;
  for(const key of ['title','status','workflow','current','change','remaining'])el(key).textContent=view[key];
  el('skills').replaceChildren(...(view.skills.length?view.skills.map(skill=>{
    const row=document.createElement('div');row.className='skill-row';
    const icon=el('skill-icon').content.cloneNode(true);row.append(icon);
    const name=document.createElement('span');name.textContent=skill.name;row.append(name);
    const state=document.createElement('span');state.className='skill-state';state.textContent='已加载';row.append(state);
    return row;
  }):[Object.assign(document.createElement('span'),{className:'placeholder',textContent:'未记录专项 Skill'})]));
  el('verification').replaceChildren(...view.verification.map(item=>{
    const span=document.createElement('span');span.className=`verification-${item.kind}`;span.textContent=item.text;return span;
  }));
  el('evidence').textContent=`验证依据（Agent 申报）：${view.evidence}`;
  el('steps').replaceChildren(...snapshot.steps.map(step=>line(stepNames[step.status],step.label)));
  el('loads').replaceChildren(...view.receipts.map(receipt=>line(time(receipt.loaded_at),receipt.name,`已读取 · ${receipt.sha256.slice(0,8)}`)));
  el('load-empty').hidden=view.receipts.length>0;
  el('history').replaceChildren(...(snapshot.history??[]).slice(-6).reverse().map(event=>line(time(event.at),event.kind==='skill_loaded'?`已加载 ${event.skill}`:event.summary||'阶段更新')));
  el('updated').textContent=`最近申报 ${time(snapshot.updated_at)}`;
  el('refresh').disabled=terminal(snapshot.status);
  el('refresh').textContent=terminal(snapshot.status)?'任务已结束':poller.paused?'恢复刷新':'暂停刷新';
  stale();
}
function connection(state) {
  el('connection').hidden=state==='synced';
  el('connection').textContent={connecting:'正在连接…',synced:'',disconnected:'连接中断，保留最后状态并重试',paused:'已暂停刷新'}[state];
}
const poller=new PanelPoller({callTool:args=>app.callServerTool(args,{timeout:10000}),onSnapshot:render,onState:connection});
function context(value) {if(value?.theme)document.documentElement.dataset.theme=value.theme==='dark'?'dark':'light';}
app.ontoolresult=result=>{if(poller.bind(result.structuredContent,{replace:true}))connection(poller.paused?'paused':'synced');};
app.onhostcontextchanged=context;
let watchdog;
app.onteardown=async()=>{poller.close();clearInterval(watchdog);return{};};
el('details').onclick=()=>{
  const open=el('details').getAttribute('aria-expanded')!=='true';
  el('details').setAttribute('aria-expanded',String(open));el('records').hidden=!open;
};
el('refresh').onclick=()=>{
  if(poller.paused){poller.resume();el('refresh').textContent='暂停刷新';}
  else{poller.pause();el('refresh').textContent='恢复刷新';}
};
connection('connecting');
try {
  await app.connect();context(app.getHostContext());poller.connected();watchdog=setInterval(stale,15000);
} catch {connection('disconnected');el('empty').textContent='卡片未连接；开发工作可继续。';}
