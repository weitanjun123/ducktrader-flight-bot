import pandas as pd, json, sys, datetime as dt
d=pd.read_csv(sys.argv[1]); d=d.sort_values('checked_at_sgt'); d['cd']=d.checked_at_sgt.str[:10]
g=d.groupby('depart').price_per_person_sgd
t=pd.DataFrame({'first':d.groupby('depart').head(1).set_index('depart').price_per_person_sgd,
 'now':d.groupby('depart').tail(1).set_index('depart').price_per_person_sgd,'low':g.min(),'high':g.max()}).round(0)
t['chg']=t.now-t['first']; t=t.sort_values(['now']).reset_index()
fd=lambda s:dt.date.fromisoformat(s)
rows=[dict(dep=fd(r.depart).strftime('%-d %b'),dow=fd(r.depart).strftime('%a'),now=int(r.now),tot=int(round(r.now*7)),chg=int(r.chg),low=int(r.low),high=int(r.high),plan=r.depart=='2027-06-01') for r in t.itertuples()]
c0,c1=fd(d.cd.min()),fd(d.cd.max())
rng=f"{c0.day}–{c1.day} {c1.strftime('%b %Y')}"
print(json.dumps(dict(rows=rows,rng=rng,n=len(d),lo=float(t.low.min()),hi=float(t.high.max()))))
