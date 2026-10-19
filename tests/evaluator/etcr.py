"""Evaluate independently judged agent runs, not hook unit-test passes."""
import argparse, json, math
FIELDS=('acceptance_met','constraints_met','no_major_rework')
def evaluate(report):
 rows=report['tasks']
 if not rows: raise ValueError('empty test set')
 ids=[r['id'] for r in rows]
 if len(ids)!=len(set(ids)): raise ValueError('duplicate task ids')
 for r in rows:
  if any(type(r.get(k)) is not bool for k in FIELDS): raise ValueError('all judgments must be booleans')
  for k in ('seconds','tokens'):
   v=r.get(k)
   if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0): raise ValueError('invalid cost')
 result={'suite':report['suite'],'version':report['version'],'total':len(rows),'etcr':100*sum(all(r[k] for k in FIELDS) for r in rows)/len(rows)}
 for k in ('seconds','tokens'):
  values=[r[k] for r in rows if r.get(k) is not None]
  result['mean_'+k]=sum(values)/len(values) if values else None
  result[k+'_coverage']=len(values)/len(rows)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('report'); p.add_argument('--baseline'); a=p.parse_args()
 report=json.load(open(a.report)); result=evaluate(report)
 if a.baseline:
  old=json.load(open(a.baseline))
  if old['suite']!=report['suite'] or sorted(t['id'] for t in old['tasks'])!=sorted(t['id'] for t in report['tasks']): raise ValueError('comparison requires the same suite and tasks')
  result['etcr_delta_pp']=result['etcr']-evaluate(old)['etcr']
 print(json.dumps(result,indent=2))
