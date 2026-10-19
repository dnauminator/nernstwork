#!/usr/bin/env python3
"""Least-squares calibration of parallel-branch + catalyst-state models to the Liao 2025 curves.

Usage: python scripts/calibrate_liao.py data/real
Reproduces the numbers in docs/SPEC.md section 7. Single-start grid, no uncertainty estimate: a sanity
calibration, not an inference result."""
import json, numpy as np
from scipy.optimize import least_squares
from scipy.integrate import solve_ivp
import sys
D = sys.argv[1].rstrip("/") + "/"  # data/real
def load(n):
    d=json.load(open(D+n+".json")); t=np.array(d["series"][0]["t_min"]); Y={s["species"]:np.array(s["y"],float) for s in d["series"]}
    return t, np.vstack([Y["NO3"],Y["NO2"],Y["NH3"]])
def sim(p,t,mode,c0,leak):
    k1,k2,k3,kl,tau=np.exp(p)
    def a(tt):
        return 1-np.exp(-tt/tau) if mode=="act" else (np.exp(-tt/tau) if mode=="deact" else 1.0)
    def rhs(_t,y):
        n3,n2,nh,s=y; g=a(_t)
        r1,r3,r2=g*k1*n3,g*k3*n3,g*k2*n2; rl=g*kl*n3 if leak else 0
        return [-r1-r3-rl,r1-r2,r3+r2,rl]
    return solve_ivp(rhs,(0,t.max()),[c0,0,0,0],t_eval=t,method="LSODA",rtol=1e-8,atol=1e-10).y
def fit(name,mode,leak):
    t,obs=load(name); c0=obs[0,0]; sc=np.maximum(obs.max(1),1e-9)[:,None]; best=None
    for a in (-6,-4):
      for b in (-6,-4):
        for tau in (3,5,7):
          x0=[a,-3,b,-6,tau]
          try: r=least_squares(lambda p:((sim(p,t,mode,c0,leak)[:3]-obs)/sc).ravel(),x0,bounds=([-14]*4+[-2],[3]*4+[12]))
          except Exception: continue
          if best is None or r.cost<best.cost: best=r
    m=sim(best.x,t,mode,c0,leak); rms=np.sqrt(((m[:3]-obs)**2).mean(1)); k=np.exp(best.x)
    print(f"{name[8:26]:18s} {mode:5s} leak={leak!s:5s} cost={best.cost:.4f} rmse(NO3,NO2,NH3)={rms.round(2)} k1={k[0]:.1e} k2={k[1]:.1e} k3(direct NH3)={k[2]:.1e} kl={k[3]:.1e} tau={k[4]:.0f} sink_end={m[3,-1]:.1f}")
fit("liao2025_agmos2_suppfig49","act",False)
fit("liao2025_agmos2_suppfig49","none",False)
for n in ("liao2025_wmos2_suppfig50a","liao2025_mos2_suppfig50b"):
    fit(n,"deact",False); fit(n,"deact",True)
