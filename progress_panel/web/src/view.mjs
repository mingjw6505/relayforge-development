export const statusNames={running:'进行中',waiting:'等待你',completed:'已完成',blocked:'受阻',cancelled:'已取消'};
const verificationNames={not_run:'未执行',running:'验证中',passed:'检查通过',failed:'检查失败',partial:'部分验证',skipped:'已跳过',unavailable:'结果不可用'};

export function cardView(snapshot) {
  const info=snapshot.details??{};
  const receipts=(snapshot.skill_loads??[]).filter(item=>item.source==='mcp_skill_load'&&typeof item.name==='string'&&/^[a-f0-9]{64}$/.test(item.sha256));
  const workflow=receipts.some(item=>item.kind==='workflow'&&item.name===snapshot.workflow)?snapshot.workflow:'未记录';
  const verification=info.verification?.source==='agent_declared'?info.verification:null;
  const counts=[];
  if(verification?.evidence) {
    for(const [key,label] of [['passed','项通过'],['failed','项失败'],['pending','项待验']]) {
      if(Number.isSafeInteger(verification[key])&&verification[key]>=0)counts.push({kind:key,text:`${verification[key]} ${label}`});
    }
  }
  if(counts.length&&verification.status!=='passed') {
    counts.unshift({kind:verification.status,text:verificationNames[verification.status]});
  }
  const remaining=snapshot.steps.filter(step=>['pending','blocked'].includes(step.status)).map(step=>step.label);
  return {
    title:snapshot.title,
    status:snapshot.status==='running'&&verification?.status==='running'?'验证中':statusNames[snapshot.status],
    workflow, receipts, skills:receipts.filter(item=>item.kind==='skill'),
    current:info.current||snapshot.steps.find(step=>step.status==='active')?.label||(snapshot.status==='completed'?'本次任务已结束':'未申报'),
    change:info.change||snapshot.summary||'未申报',
    remaining:info.remaining||(remaining.length?remaining.slice(0,3).join('、')+(remaining.length>3?'…':''):'未申报'),
    verification:counts.length?counts:[{kind:verification?.status??'not_run',text:verificationNames[verification?.status]??'未执行'}],
    evidence:verification?.evidence||'未提供验证依据',
  };
}
