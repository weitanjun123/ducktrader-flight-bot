import pandas as pd, json, sys, datetime as dt
d=pd.read_csv(sys.argv[1]); d['cd']=d.checked_at_sgt.str[:10]
cols=sorted(d.cd.unique())
p=d.pivot_table(index='depart',columns='cd',values='price_per_person_sgd',aggfunc='min').reindex(columns=cols)
rows=[[i,[None if pd.isna(v) else int(round(v)) for v in r]] for i,r in p.iterrows()]
d['diff']=d.price_per_person_sgd-d.groupby('depart').price_per_person_sgd.transform('median')
DOW=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
m=d.pivot_table(index='check_dow',columns='check_hour_sgt',values='diff',aggfunc='mean').reindex(DOW).reindex(columns=range(24))
M={k:[None if pd.isna(v) else round(float(v),1) for v in r] for k,r in m.iterrows()}
cells=[(v,k,h) for k,r in M.items() for h,v in enumerate(r) if v is not None]
fh=lambda h:('12am' if h==0 else f'{h}am' if h<12 else '12pm' if h==12 else f'{h-12}pm')
cheap=sorted(cells)[:3]; dear=sorted(cells)[-1]
gap=max(abs(c[0]) for c in cells)
lat=d.sort_values('checked_at_sgt').groupby('depart').tail(1)
mn=lat.price_per_person_sgd.min(); cheapest=lat[lat.price_per_person_sgd<=mn+0.5].depart.tolist()
plan=lat[lat.depart=='2027-06-01'].price_per_person_sgd.iloc[0]
save=round((plan-mn)*7/10)*10
fmt=lambda s:dt.date.fromisoformat(s).strftime('%a %-d %b')
lo=float(d.price_per_person_sgd.min()); hi=float(d.price_per_person_sgd.max())
c0=dt.date.fromisoformat(cols[0]); c1=dt.date.fromisoformat(cols[-1])
out=dict(D={'cols':[dt.date.fromisoformat(c).strftime('%-d') for c in cols],'rows':rows},M=M,lo=lo,hi=hi,
  tip_cheap=' · '.join(f"{k} {fh(h)}" for v,k,h in cheap), tip_dear=f"{dear[1]} {fh(dear[2])}",
  gap=int(gap+0.999), ndays=len(cols), card1=f"S${mn:,.0f}", card1t="Cheapest: "+" & ".join(fmt(x) for x in cheapest[:2]),
  card2=f"S${plan:,.0f}", save=f"S${save:,.0f}", savet=f"Saved for 7 by flying {fmt(cheapest[0]).split(' ',1)[1]}",
  range=f"{c0.day}–{c1.day} {c1.strftime('%b %Y')}" if c0.month==c1.month else f"{c0.strftime('%-d %b')}–{c1.strftime('%-d %b %Y')}",
  nchecks=len(d), month=c1.strftime('%b').upper())
print(json.dumps(out))
