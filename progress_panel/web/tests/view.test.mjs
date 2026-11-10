import test from 'node:test';
import assert from 'node:assert/strict';
import {cardView, historyView} from '../src/view.mjs';
const base={title:'修复重试',status:'running',summary:'已定位原因',steps:[{label:'修复',status:'active'},{label:'验证',status:'pending'}]};
const receipt=(name,kind='skill')=>({name,kind,source:'mcp_skill_load',sha256:'a'.repeat(64)});

test('loaded workflow Skills remain visible when no specialist Skill was loaded',()=>{
  const view=cardView({...base,workflow:'finishing-development',skill_loads:[
    receipt('task-router','workflow'),receipt('development-workflow','workflow'),receipt('finishing-development','workflow'),
  ]});
  assert.equal(view.workflow,'finishing-development');
  assert.deepEqual(view.skills.map(item=>item.name),['task-router','development-workflow','finishing-development']);
});

test('old snapshots and missing evidence do not invent workflow or Skill use',()=>{
  const view=cardView({...base,workflow:'development-workflow',skill_loads:[{name:'planned',kind:'skill',source:'planned'}]});
  assert.equal(view.workflow,'未记录');assert.deepEqual(view.skills,[]);
  assert.equal(view.current,'修复');assert.equal(view.remaining,'验证');
  assert.equal(view.verification[0].text,'未执行');
});
test('receipt-backed names and separately declared verification reach the compact view',()=>{
  const view=cardView({...base,workflow:'development-workflow',skill_loads:[receipt('development-workflow','workflow'),receipt('systematic-debugging')],details:{current:'验证重试',change:'补齐幂等校验',remaining:'超时恢复',verification:{status:'partial',passed:18,pending:2,evidence:'相关回归结果',source:'agent_declared'}}});
  assert.equal(view.workflow,'development-workflow');
  assert.deepEqual(view.skills.map(item=>item.name),['development-workflow','systematic-debugging']);
  assert.equal(view.current,'验证重试');assert.deepEqual(view.verification.map(item=>item.text),['部分验证','18 项通过','2 项待验']);
});

test('only task-scoped load receipts reach the Skill list',()=>{
  const view=cardView({...base,skill_loads:[receipt('task-router','workflow'),
    {...receipt('planned'),source:'planned'}, {...receipt('bad-hash'),sha256:''},
    receipt('unknown-kind','other'),receipt('systematic-debugging')],
  });
  assert.deepEqual(view.skills.map(item=>item.name),['task-router','systematic-debugging']);
  assert.equal(cardView({...base,skill_loads:[]}).skills.length,0);
});
test('completed work cannot imply passed verification or replace partial results',()=>{
  const done={...base,status:'completed',steps:[{label:'修复',status:'done'}]};
  assert.equal(cardView(done).verification[0].text,'未执行');
  assert.equal(cardView({...done,details:{verification:{status:'partial',source:'agent_declared',evidence:'仍有未覆盖场景'}}}).verification[0].text,'部分验证');
  assert.equal(cardView({...done,details:{verification:{status:'passed',passed:20,source:'planned'}}}).verification[0].text,'未执行');
});

test('a failed overall check remains visible even when some test counts passed',()=>{
  const view=cardView({...base,status:'completed',details:{verification:{status:'failed',passed:20,evidence:'20 个用例通过，但另一项检查失败',source:'agent_declared'}}});
  assert.ok(view.verification.some(item=>item.text==='检查失败'));
  assert.ok(view.verification.some(item=>item.text==='20 项通过'));
  assert.match(view.attention,/检查失败/);
});

test('collapsed cards retain verification gaps without treating completion as a pass',()=>{
  assert.equal(cardView(base).attention,'');
  const complete={...base,status:'completed'};
  assert.equal(cardView(complete).attention,'验证：未执行');
  assert.match(cardView({...complete,details:{verification:{status:'partial',source:'agent_declared'}}}).attention,/部分验证/);
  assert.equal(cardView({...complete,details:{verification:{status:'passed',source:'agent_declared'}}}).attention,'');
  assert.equal(cardView({...complete,details:{verification:{status:'passed',source:'planned'}}}).attention,'验证：未执行');
});

test('terminal views ignore stale actions and preserve partial verification',()=>{
  const snapshot={...base,status:'completed',summary:'修复已完成',steps:[{label:'修复',status:'done'}],details:{current:'正在修复',remaining:'修复后验证',verification:{status:'partial',source:'agent_declared',evidence:'仍有场景未覆盖'}}};
  const view=cardView(snapshot);
  assert.equal(view.currentLabel,'结果');
  assert.equal(view.current,'修复已完成');
  assert.equal(view.remaining,'无（本次范围）');
  assert.equal(view.verification[0].text,'部分验证');
  assert.equal(cardView({...snapshot,status:'cancelled'}).remaining,'已停止（本次尝试）');
});

test('waiting labels identify who is needed and blocked views use the blocked step',()=>{
  assert.equal(cardView({...base,status:'waiting'}).status,'等待中');
  const external=cardView({...base,status:'waiting',details:{waiting_for:'external',reason:'等待构建结果',remaining:'构建结束后验收'}});
  assert.equal(external.status,'等待外部结果');
  assert.equal(external.current,'等待构建结果');
  assert.equal(cardView({...base,status:'waiting',details:{waiting_for:'user'}}).status,'等待你确认');
  assert.equal(cardView({...base,status:'blocked',steps:[{label:'获取验收环境',status:'blocked'}],details:{current:'旧动作'}}).current,'获取验收环境');
});

test('history uses recorded details and never invents missing legacy information',()=>{
  const event={revision:2,status:'running',current_step:'验证',details:{current:'验证重试',change:'已修复重复提交',verification:{status:'partial',source:'agent_declared',evidence:'未覆盖断网'}}};
  const view=historyView(event);
  assert.equal(view.title,'已修复重复提交');
  assert.equal(view.current,'验证重试');
  assert.equal(view.evidence,'未覆盖断网');
  assert.equal(historyView({status:'completed',summary:'交付完成'}).title,'交付完成');
  assert.equal(historyView({status:'running',summary:''}).evidence,'');
  assert.equal(historyView({status:'blocked',summary:'等待恢复',details:{reason:'缺少验收环境'}}).reason,'缺少验收环境');
});

test('mode and selected method phases are distinct from loaded workflow and task steps',()=>{
  const snapshot={...base,execution_mode:'L2',workflow:'finishing-development',skill_loads:[receipt('finishing-development','workflow')],details:{current:'正在生成规格文档'},method_progress:[{
    method:'sdd',status:'running',source:'agent_declared',phases:[{label:'范围确认',status:'done'},{label:'规格文档',status:'active'},{label:'实施计划',status:'pending'}],
  }]};
  const view=cardView(snapshot);
  assert.equal(view.mode,'Standard / L2');
  assert.equal(view.current,'正在生成规格文档');
  assert.equal(view.methods[0].title,'SDD · 规格驱动');
  assert.equal(view.methods[0].current,'规格文档 · 进行中');
  assert.equal(view.methods[0].done,1);
  assert.equal(view.methods[0].total,3);
  assert.equal(view.workflow,'finishing-development');
  assert.equal(cardView({...base,execution_mode:'L1'}).mode,'Quick / L1');
  assert.equal(cardView({...base,execution_mode:'L3'}).mode,'Large / L3');
});

test('unknown declarations stay unknown and method completion does not imply tests passed',()=>{
  const old=cardView({...base,workflow:'development-workflow',skill_loads:[receipt('development-workflow','workflow')]});
  assert.equal(old.mode,'未申报');
  assert.equal(cardView({...base,execution_mode:'toString'}).modeDescription,'');
  assert.deepEqual(old.methods,[]);
  const view=cardView({...base,status:'completed',execution_mode:'L2',method_progress:[{method:'sdd',status:'completed',source:'agent_declared',phases:[{label:'规格',status:'done'},{label:'发布',status:'skipped'}]}]});
  assert.equal(view.methods[0].current,'已完成');
  assert.equal(view.methods[0].skipped,1);
  assert.equal(view.verification[0].text,'未执行');
  assert.deepEqual(cardView({...base,method_progress:[{method:'sdd',source:'planned',phases:[]}]}).methods,[]);
});

const use=(skill,via='direct_read')=>({skill,via,source:'agent_declared',recorded_at:'2026-11-10T10:00:00Z'});
test('external/direct-read/host declarations appear beside verified bundled loads',()=>{
  const view=cardView({...base,skill_loads:[receipt('task-router','workflow')],skill_uses:[use('host:imagegen'),use('other-plugin:design','skill_tool'),use('host:openai-docs','context')]});
  assert.deepEqual(view.skills.map(item=>item.name),['task-router','imagegen','design','openai-docs']);
  assert.equal(view.workflow,'未记录');
  assert.equal(view.skills[0].records[0].source,'mcp_skill_load');
  assert.equal(view.skills[1].records[0].source,'agent_declared');
  assert.match(view.skills[1].records[0].label,/直接读取.*Agent/);
  assert.equal(view.skills[1].records[0].digest,undefined);
});
test('the same qualified Skill merges evidence while equal names from different providers stay distinct',()=>{
  const view=cardView({...base,skill_loads:[receipt('frontend-design')],skill_uses:[use('relayforge-development:frontend-design'),use('host:frontend-design'),use('host:frontend-design','skill_tool')]});
  assert.deepEqual(view.skills.map(item=>item.name),['relayforge-development:frontend-design','host:frontend-design']);
  assert.equal(view.skills[0].records.length,2);
  assert.equal(view.skills[1].records.length,2);
});
test('unverified provenance and planned metadata never enter usage records',()=>{
  const view=cardView({...base,skill_uses:[{...use('host:planned'),source:'planned'}, {...use('host:forged'),source:'mcp_skill_load'},use('host:later','planned'),use('/private/secret'),{skill:'host:missing-evidence',via:'direct_read',source:'agent_declared'}]});
  assert.deepEqual(view.skills,[]);
});
test('history shows only use declarations recorded at that milestone',()=>{
  const view=historyView({status:'running',skill_uses:[use('host:imagegen')]});
  assert.match(view.skillUses.join(' '),/host:imagegen.*直接读取/);
  assert.deepEqual(historyView({status:'running'}).skillUses,[]);
});
