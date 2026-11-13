#!/usr/bin/env python3
"""DOLENT profile V2: five independent SVG panels.

No pip dependencies. GitHub Actions fetches public profile contribution data.
For a local offline sample: python scripts/render_dashboard.py --demo
Demo output is clearly watermarked and must not be treated as real statistics.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from html import escape
import json
import math
import os
from pathlib import Path
import random
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
LOGIN = os.getenv('GITHUB_LOGIN', 'zwordup-sudo')
W = 1200
FONT = '"DejaVu Sans Mono", "Liberation Mono", monospace'
C = {
    'bg':'#080D16','panel':'#0B1420','panel2':'#0D1925','border':'#263D50',
    'line':'#173046','white':'#EEF6F9','soft':'#A6BED0','dim':'#668397',
    'cyan':'#22DDEA','teal':'#0AB9B7','green':'#24E78F','lime':'#C2EF48',
    'yellow':'#FBE24D','orange':'#FF983C','red':'#FF5367','purple':'#B176FF',
}


def demo_data():
    rng = random.Random(8231)
    today = date.today()
    start = today-timedelta(days=364)
    days=[]
    for k in range(365):
        d=start+timedelta(days=k)
        wave=0.6*math.sin(k/19)**2
        hills=sum(max(0,1-abs(k-c)/16)*h for c,h in [(45,4),(113,9),(176,12),(237,5),(285,17),(342,8)])
        n=max(0, round((rng.random()-.53)*4+wave+hills))
        days.append({'date':d.isoformat(),'contributionCount':n})
    return {'days':days,'total':sum(d['contributionCount'] for d in days),'repos':2,'demo':True}


def github_data():
    token=os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not token:
        raise RuntimeError('Missing GITHUB_TOKEN; run --demo only for a labeled sample.')
    query='''query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
        repositories(first: 1, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false) {
          totalCount
        }
      }
    }'''
    body=json.dumps({'query':query,'variables':{'login':LOGIN}}).encode('utf-8')
    req=urllib.request.Request('https://api.github.com/graphql',body,{
        'Authorization':f'Bearer {token}',
        'Content-Type':'application/json',
        'Accept':'application/vnd.github+json',
        'User-Agent':'dolent-modular-readme',
    },method='POST')
    with urllib.request.urlopen(req,timeout=30) as response:
        payload=json.load(response)
    if payload.get('errors'):
        raise RuntimeError('GitHub GraphQL: '+str(payload['errors']))
    u=(payload.get('data') or {}).get('user')
    if not u:
        raise RuntimeError(f'No GitHub profile found for: {LOGIN}')
    cal=u['contributionsCollection']['contributionCalendar']
    days=[d for wk in cal['weeks'] for d in wk['contributionDays']]
    return {'days':days,'total':cal['totalContributions'],
            'repos':u['repositories']['totalCount'],'demo':False}


class SVG:
    def __init__(self,height,desc):
        self.h=height
        self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" aria-label="{escape(desc,quote=True)}">']
        self.add('''<defs>
          <linearGradient id="back" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0C1B29"/><stop offset=".57" stop-color="#080D16"/><stop offset="1" stop-color="#100E1D"/></linearGradient>
          <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#17E0E7"/><stop offset=".65" stop-color="#153A63"/><stop offset="1" stop-color="#102734"/></linearGradient>
          <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" stroke="#254457" stroke-opacity=".28" fill="none" stroke-width=".7"/></pattern>
          <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse"><path d="M0 2.4H1200" stroke="#000" stroke-opacity=".35" stroke-width=".4"/></pattern>
          <radialGradient id="aura"><stop stop-color="#20D6E9" stop-opacity=".27"/><stop offset="1" stop-color="#20D6E9" stop-opacity="0"/></radialGradient>
        </defs>''')
        self.rect(0,0,W,height,'url(#back)')
        self.rect(1.5,1.5,W-3,height-3,'none',C['border'],1.7,14)
        self.line(28,15,102,15,C['cyan'],2)
        self.line(W-128,height-15,W-28,height-15,C['purple'],2)
    def add(self,x): self.s.append(x)
    def rect(self,x,y,w,h,fill='none',stroke=None,sw=1,r=0,extra=''):
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{r}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+f' {extra}/>')
    def line(self,x1,y1,x2,y2,color,sw=1,alpha=1,dash=''):
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{sw}" opacity="{alpha}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def path(self,d,color,sw=1,fill='none',alpha=1,extra=''):
        self.add(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}" opacity="{alpha}" {extra}/>')
    def circle(self,x,y,r,fill='none',stroke='none',sw=1,extra=''):
        self.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
    def text(self,x,y,t,size=20,color=None,weight=400,extra=''):
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-family={repr(FONT)} font-size="{size}" font-weight="{weight}" fill="{color or C["white"]}" {extra}>{escape(str(t),quote=False)}</text>')
    def poly(self,coords,fill,stroke='none',sw=1):
        points=' '.join(f'{x:.2f},{y:.2f}' for x,y in coords)
        self.add(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def pane(self,x,y,w,h,accent=C['cyan']):
        self.rect(x,y,w,h,C['panel'],C['border'],1.1,10)
        self.path(f'M{x+13} {y+28} V{y+13} H{x+113}',accent,2)
        self.line(x+w-83,y+14,x+w-14,y+14,accent,1.2,.65)
    def save(self,name,demo=False):
        if demo:
            self.rect(W-251,26,210,29,'#421F25',C['orange'],1,5)
            self.text(W-238,47,'DEMO / SAMPLE DATA',15,C['yellow'],700)
        self.add(f'<rect width="{W}" height="{self.h}" fill="url(#scan)" opacity=".12" pointer-events="none"/>')
        self.add('</svg>')
        dest=ASSETS/name
        dest.write_text('\n'.join(self.s),encoding='utf-8')
        print(f'Wrote {dest.name} ({dest.stat().st_size:,} bytes)')


def title(s,label,subtitle=''):
    s.text(30,43,label,21,C['white'],700)
    if subtitle:s.text(1168,43,subtitle,14,C['soft'],400,'text-anchor="end"')
    s.line(30,57,1170,57,C['border'],1)


def render_header(demo):
    s=SVG(275,'DOLENT developer profile hero and system identity')
    s.rect(24,24,266,226,'#081824',C['border'],1.3,9)
    s.rect(33,33,248,208,'url(#grid)')
    s.circle(157,127,80,'url(#sky)',C['cyan'],1.2)
    s.circle(157,127,95,'none','#266276',1)
    s.circle(157,127,105,'none','#244B5C',.8)
    for i in range(6):
        y=72+20*i
        s.path(f'M{78+i*2} {y} Q{152} {y+20} {237-i*2} {y-3}',C['cyan'],.7,alpha=.24)
    s.poly([(38,230),(81,182),(110,199),(139,142),(158,162),(199,109),(229,170),(259,150),(278,228)],'#102739','#2199B7',1.5)
    s.path('M42 231 L82 185 L108 204 L139 149 L157 168 L201 115 L229 178 L258 154 L276 228',C['orange'],2.3,alpha=.85)
    for x,y in [(69,56),(242,62),(260,206),(51,103),(185,46)]:
        s.line(x-5,y,x+5,y,C['cyan'],.8,.6);s.line(x,y-5,x,y+5,C['cyan'],.8,.6)
    s.text(322,58,'SYSTEM IDENTITY  /  001',19,C['cyan'],600)
    s.text(315,139,'DOLENT_',77,C['white'],700)
    s.text(323,174,'DEVELOPER  /  AI SYSTEMS  /  MOBILE ENGINEERING',20,C['soft'],500)
    s.line(323,200,1153,200,C['border'],1)
    for idx,(v,col) in enumerate([('PYTHON',C['yellow']),('KOTLIN',C['purple']),('TYPESCRIPT',C['cyan']),('AI AGENTS',C['green'])]):
        x=325+idx*178
        w=158 if idx!=2 else 168
        s.rect(x,214,w,30,'#12212D',col,.9,6)
        s.text(x+w/2,235,v,15,col,700,'text-anchor="middle"')
    s.circle(1080,74,7,C['green'])
    s.text(1100,80,'ONLINE',19,C['green'],700)
    s.text(1139,171,'SESSION 001',15,C['dim'],400,'text-anchor="end"')
    s.save('header.svg',False)


def render_project(name,tagline,stack,number,color,status,mark):
    s=SVG(155,f'DOLENT project archive {number}: {name}')
    s.rect(18,18,1164,119,C['panel'],C['border'],1.1,10)
    s.rect(32,34,94,85,'#11212D',color,1,7)
    s.text(79,93,mark,56,color,700,'text-anchor="middle"')
    s.text(156,50,f'0{number}  //  PROJECT ARCHIVE',17,color,700)
    s.text(153,88,name,39,C['white'],700)
    s.text(153,115,tagline,19,C['soft'])
    s.circle(963,53,5,color)
    s.text(981,60,status,17,color,700)
    s.text(1143,116,stack,17,C['dim'],500,'text-anchor="end"')
    for i in range(7):
        bh=11+(i*i*13+number*11)%35
        s.rect(1052+i*15,91-bh,8,bh,color,extra=f'opacity="{.30+i*.08:.2f}"')
    s.save('project-fryd.svg' if number==1 else 'project-hercules.svg')


def clamp(v,a=0,b=1):return max(a,min(b,v))

def ramp(t):
    if t < .14: return '#1F5464'
    if t < .29: return '#24A9C5'
    if t < .44: return C['teal']
    if t < .59: return C['green']
    if t < .73: return C['lime']
    if t < .86: return C['yellow']
    if t < .95: return C['orange']
    return C['red']


def heat_count(n,top):
    if n<=0:return '#122B3A'
    return ramp(.31+.69*clamp(n/max(1,top)))


def gather_weeks(data):
    by_day={d['date']:int(d['contributionCount']) for d in data['days']}
    dates=sorted(date.fromisoformat(x) for x in by_day)
    if not dates:return [0]*53
    sunday=dates[0]-timedelta(days=(dates[0].weekday()+1)%7)
    weeks=[]
    for wk in range(math.ceil((dates[-1]-sunday).days/7)+1):
        wstart=sunday+timedelta(days=wk*7)
        weeks.append(sum(by_day.get((wstart+timedelta(days=dd)).isoformat(),0) for dd in range(7)))
    return weeks


def render_terrain(data):
    s=SVG(520,'DOLENT colorful mountain contour visualization of weekly GitHub activity')
    title(s,'03  //  ACTIVITY TERRAIN', 'PREVIEW / SYNTHETIC DATA' if data['demo'] else 'WEEKLY ACTIVITY / VISUAL INTERPRETATION')
    s.rect(30,74,1140,422,'#091522',C['border'],1,8)
    s.rect(31,75,1138,420,'url(#grid)')
    s.circle(595,290,255,'url(#aura)')
    s.text(54,112,'TOPOGRAPHIC SIGNAL',17,C['cyan'],700)
    s.text(55,139,'12 MONTHS',16,C['soft'])
    s.line(55,151,254,151,C['border'])
    s.text(55,189,'HEIGHT = WEEKLY ACTIVITY',14,C['dim'])
    s.text(55,216,'COLOR = RELATIVE INTENSITY',14,C['dim'])
    # chart floor; perspective bands
    cx=680;base_y=411;rx=465;ry=72
    s.add(f'<ellipse cx="{cx}" cy="{base_y}" rx="{rx}" ry="{ry}" fill="#0B1D29" stroke="#477387" stroke-width="1.2"/>')
    for i in range(1,6):
        s.add(f'<ellipse cx="{cx}" cy="{base_y}" rx="{rx-i*65}" ry="{ry-i*10}" fill="none" stroke="#2C5060" stroke-width=".9" opacity=".7"/>')
    weeks=gather_weeks(data)
    if not weeks:weeks=[0]*53
    order=sorted(weeks)
    top=max(1,order[min(len(order)-1,int((len(order)-1)*.93))])
    norm=[clamp(math.log1p(v)/math.log1p(top)) for v in weeks]
    # Smooth neighboring bins with a Gaussian kernel to make a natural geological silhouette.
    def activity(u):
        pos=clamp(u)* (len(norm)-1)
        sm=0.;den=0.
        for k in range(max(0,int(pos)-9),min(len(norm),int(pos)+11)):
            ww=math.exp(-((k-pos)/2.9)**2/2)
            sm+=norm[k]*ww;den+=ww
        return sm/max(.01,den)
    # place contours from back to front; separate gradients for each line fragment
    # Dominant localized hills turn active weeks into isolated topo peaks.
    top_weeks=[]
    for ix in sorted(range(len(weeks)), key=lambda k:weeks[k], reverse=True):
        if weeks[ix] and all(abs(ix-j)>9 for j in top_weeks):
            top_weeks.append(ix)
        if len(top_weeks)>=4:
            break
    peak_z=[.58, .44, .64, .50]
    peak_sources=[((ix/max(1,len(weeks)-1))*2-1, peak_z[n], .24+.79*norm[ix])
                  for n,ix in enumerate(top_weeks)]
    def surf(x,z):
        u=clamp((x+1)/2)
        hz=.042+.13*activity(u)
        for k,(px,pz,power) in enumerate(peak_sources):
            width=.10+(k%2)*.05
            depth=.23
            distance=((x-px)/width)**2+((z-pz)/depth)**2
            hz+=power*math.exp(-distance*.69)
        hz+=.024*math.sin(15*u+5*z)**2
        return clamp(hz)
    # peak height at x depends only on real weekly input, z controls view perspective
    for iz in range(40,-1,-1):
        z=iz/40
        pts=[]
        span=.98-(z-.5)**2*.27
        for ix in range(171):
            ux=ix/170
            xx=(ux*2-1)*span
            alt=surf(xx,z)
            screenx=cx+xx*460
            screeny=base_y + (.5-z)*174 - 207*alt*(.80+.2*z)
            pts.append((screenx,screeny,alt))
        for a,b in zip(pts,pts[1:]):
            col=ramp((a[2]+b[2])*.53)
            s.line(a[0],a[1],b[0],b[1],col,1.1,.44+.51*z)
    # peak markers use real week activity numbers, spaced to avoid label overlaps
    chosen=top_weeks[:3]
    for idx in sorted(chosen):
        u=idx/max(1,len(weeks)-1)
        x=u*2-1
        z=peak_z[top_weeks.index(idx)]
        X=cx+x*460
        Y=base_y+(.5-z)*174-207*surf(x,z)*(.80+.2*z)
        Y=max(153,min(390,Y))
        col=ramp(.31+.69*clamp(weeks[idx]/max(1,top)))
        s.circle(X,Y,7,col,C['white'],1.8)
        s.line(X,Y-7,X,Y-43,col,1.8,.88)
        label=f'{weeks[idx]} / WK'
        labw=119
        s.rect(X-labw/2,Y-79,labw,29,'#10212D',col,1,5)
        s.text(X,Y-59,label,16,col,700,'text-anchor="middle"')
    # an abstract dotted expedition line, intentionally decorative, not data
    s.path('M272 420 C420 385 476 442 575 360 S796 369 902 304 S1026 359 1138 315','#E7FFF4',2.4,alpha=.6,extra='stroke-dasharray="8 9"')
    s.text(1008,470,'SIGNAL RANGE',14,C['soft'])
    for k in range(7):s.rect(997+k*23,482,18,9,ramp(k/6),r=2)
    s.text(56,473,'ILLUSTRATIVE RELIEF GENERATED FROM WEEKLY COUNTS',13,C['dim'])
    s.save('terrain.svg',False)


def render_activity(data):
    s=SVG(346,'GitHub activity statistics and 12-month contribution heatmap')
    title(s,'04  //  CONTRIBUTION MAP', 'PREVIEW / SYNTHETIC DATA' if data['demo'] else 'CALENDAR / DAILY CONTRIBUTIONS')
    s.pane(26,75,245,245,C['purple'])
    active=sum(int(d['contributionCount'])>0 for d in data['days'])
    pairs=[('TOTAL CONTRIB.',str(data['total']),C['green']),
           ('ACTIVE DAYS',str(active),C['orange']),
           ('PUBLIC REPOS',str(data['repos']),C['purple'])]
    for i,(k,v,c) in enumerate(pairs):
        y=114+i*72
        s.text(44,y,k,15,C['soft'])
        s.text(44,y+37,v,33,c,700)
        if i<2:s.line(42,y+51,250,y+51,C['border'])
    s.pane(287,75,887,245,C['cyan'])
    s.text(309,111,'CONTRIBUTION INTENSITY',17,C['white'],700)
    s.text(964,111,'LOW',14,C['dim'])
    for i in range(8):s.rect(1015+i*12,98,10,12,ramp(i/7),r=2)
    s.text(1161,111,'HIGH',14,C['soft'],400,'text-anchor="end"')
    by_day={d['date']:max(0,int(d['contributionCount'])) for d in data['days']}
    parsed=sorted(date.fromisoformat(d) for d in by_day)
    if not parsed:
        s.save('activity.svg',False);return
    last=parsed[-1]
    # Sunday-aligned exact 53 columns. The date window comes from GitHub's calendar.
    first=last-timedelta(days=364)
    first-=timedelta(days=(first.weekday()+1)%7)
    weeks=math.ceil((last-first).days/7)+1
    # scale to exactly fit panel width in case GitHub calendar includes 54 weeks
    available=825;gap=3.0; cell=min(13.5,(available/max(1,weeks))-gap)
    x0=332; y0=167
    vals=sorted(by_day.values())
    p95=max(1,vals[min(len(vals)-1,int((len(vals)-1)*.95))])
    prev_month=None
    for wk in range(weeks):
        sunday=first+timedelta(days=7*wk)
        if sunday.month!=prev_month:
            if wk<weeks-1:
                s.text(x0+wk*(cell+gap),150,sunday.strftime('%b').upper(),13,C['soft'])
            prev_month=sunday.month
        for dow in range(7):
            dd=sunday+timedelta(days=dow)
            if dd>last or dd<parsed[0]:continue
            cnt=by_day.get(dd.isoformat(),0)
            s.rect(x0+wk*(cell+gap),y0+dow*19,cell,13,heat_count(cnt,p95),r=2)
    for weekday,yy in [('SUN',178),('TUE',216),('THU',254),('SAT',292)]:
        s.text(302,yy,weekday,12,C['dim'])
    s.text(309,306,'RED = HIGHER ACTIVITY · NOT A WARNING',13,C['soft'])
    s.save('activity.svg',False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true',help='generate visibly labeled synthetic sample')
    args=parser.parse_args()
    ASSETS.mkdir(exist_ok=True,parents=True)
    data=demo_data() if args.demo else github_data()
    render_header(data['demo'])
    render_project('FRYD','AI PRODUCTIVITY / PERSONAL SYSTEM','TYPESCRIPT  /  PYTHON  /  AI',1,C['cyan'],'IN DEVELOPMENT','V')
    render_project('HERCULES','ANDROID FITNESS / TRAINING LOG','KOTLIN  /  COMPOSE  /  ROOM',2,C['orange'],'LOCAL PROJECT','H')
    render_terrain(data)
    render_activity(data)
    print('Mode:', 'DEMO (synthetic sample)' if data['demo'] else 'LIVE (GitHub API)')


if __name__=='__main__':main()
