import test from 'node:test';
import assert from 'node:assert/strict';
import {cardView} from '../src/view.mjs';
const base={title:'修复重试',status:'running',summary:'已定位原因',steps:[{label:'修复',status:'active'},{label:'验证',status:'pending'}]};
const receipt=(name,kind='skill')=>({name,kind,source:'mcp_skill_load',sha256:'a'.repeat(64)});

test('old snapshots and missing evidence do not invent workflow or Skill use',()=>{
  const view=cardView({...base,workflow:'development-workflow',skill_loads:[{name:'planned',kind:'skill',source:'planned'}]});
  assert.equal(view.workflow,'未记录');assert.deepEqual(view.skills,[]);
  assert.equal(view.current,'修复');assert.equal(view.remaining,'验证');
  assert.equal(view.verification[0].text,'未执行');
});
test('receipt-backed names and separately declared verification reach the compact view',()=>{
  const view=cardView({...base,workflow:'development-workflow',skill_loads:[receipt('development-workflow','workflow'),receipt('systematic-debugging')],details:{current:'验证重试',change:'补齐幂等校验',remaining:'超时恢复',verification:{status:'partial',passed:18,pending:2,evidence:'相关回归结果',source:'agent_declared'}}});
  assert.equal(view.workflow,'development-workflow');assert.equal(view.skills[0].name,'systematic-debugging');
  assert.equal(view.current,'验证重试');assert.deepEqual(view.verification.map(item=>item.text),['部分验证','18 项通过','2 项待验']);
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
});
