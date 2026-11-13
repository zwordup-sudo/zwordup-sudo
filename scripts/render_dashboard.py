#!/usr/bin/env python3
"""Render DOLENT's GitHub README dashboard with standard-library Python only.

Usage:
  python scripts/render_dashboard.py --demo
  GITHUB_TOKEN=... python scripts/render_dashboard.py

The demo is intentionally labeled PREVIEW / SYNTHETIC DATA.
GitHub Actions fetches real public contribution data via GraphQL.
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
OUT = ROOT / 'assets' / 'dashboard.svg'
LOGIN = os.getenv('GITHUB_LOGIN', 'zwordup-sudo')
WIDTH, HEIGHT = 1440, 1010
FONT = '"DejaVu Sans Mono", "Liberation Mono", monospace'
C = {
 'bg':'#080C12', 'panel':'#0B111A', 'panel2':'#0C1420', 'border':'#284255',
 'line':'#193344', 'white':'#E4F3F4', 'soft':'#8BA6B5', 'muted':'#5A7785',
 'cyan':'#35E4EC', 'blue':'#398CD9', 'green':'#33E58E', 'lime':'#B1F044',
 'yellow':'#FFD33E', 'orange':'#FF993F', 'red':'#FF4F62', 'purple':'#BD6EFF',
}


def demo_data():
    rng = random.Random(2411)
    today = date.today()
    start = today-timedelta(days=364)
    start -= timedelta(days=(start.weekday()+1)%7)
    end = today
    days=[]
    for i in range((end-start).days+1):
        d=start+timedelta(days=i)
        wave=math.sin((i-35)/30)**2 + .8*math.sin((i+54)/49)**2
        bursts=sum(max(0, 1-abs(i-pos)/13)*peak for pos,peak in [(62,8),(135,10),(213,15),(279,7),(326,17),(355,6)])
        n=max(0, round((rng.random()-0.55)*6 + wave*.9 + bursts*.85))
        days.append({'date':d.isoformat(), 'contributionCount':n})
    return {'days':days,'total':sum(x['contributionCount'] for x in days), 'repos':1,'demo':True}


def github_data():
    token=os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    if not token:
        raise RuntimeError('Missing GITHUB_TOKEN; use --demo for a labeled preview.')
    query = '''query($login: String!) {
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
    payload=json.dumps({'query':query,'variables':{'login':LOGIN}}).encode()
    req=urllib.request.Request('https://api.github.com/graphql', data=payload, headers={
        'Authorization':f'Bearer {token}', 'Content-Type':'application/json',
        'Accept':'application/vnd.github+json', 'User-Agent':'dolent-profile-dashboard',
    }, method='POST')
    with urllib.request.urlopen(req,timeout=30) as res:
        response=json.load(res)
    if 'errors' in response:
        raise RuntimeError('GitHub GraphQL error: '+str(response['errors']))
    user=response.get('data',{}).get('user')
    if user is None:
        raise RuntimeError(f'GitHub user not found: {LOGIN}')
    cal=user['contributionsCollection']['contributionCalendar']
    days=[d for w in cal['weeks'] for d in w['contributionDays']]
    return {'days':days, 'total':cal['totalContributions'], 'repos':user['repositories']['totalCount'],'demo':False}


def xmltext(t): return escape(str(t), quote=False)

class SVG:
    def __init__(self):self.parts=[]
    def add(self,s):self.parts.append(s)
    def rect(self,x,y,w,h,fill='none',stroke=None,sw=1,r=0,extra=''):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+f' {extra}/>')
    def line(self,x1,y1,x2,y2,stroke,sw=1,opacity=1,dash=''):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def path(self,d,stroke,sw=1,fill='none',opacity=1,extra=''):
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}" {extra}/>')
    def circle(self,x,y,r,fill,stroke='none',sw=1,extra=''):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
    def text(self,x,y,s,size=16,color=None,weight=400,extra=''):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color or C["white"]}" {extra}>{xmltext(s)}</text>')
    def polygon(self,pts,fill,stroke='none',sw=1,extra=''):
        self.add('<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')
    def panel(self,x,y,w,h,accent=None,shade=None):
        self.rect(x,y,w,h,shade or C['panel'],C['border'],1.3,13)
        if accent:
            self.path(f'M{x+12} {y+28} L{x+12} {y+13} Q{x+12} {y+12} {x+27} {y+12} L{x+106} {y+12}',accent,1.7)
            self.line(x+14,y+h-13,x+57,y+h-13,accent,1.3,.8)
        self.line(x+w-20,y+16,x+w-20,y+34,accent or C['border'],1,0.7)
        self.line(x+w-28,y+17,x+w-12,y+17,accent or C['border'],1,0.7)
    def label(self,x,y,s,color=None):self.text(x,y,s,15,color or C['white'],600)


def clamp(v,a=0,b=1):return max(a,min(b,v))

def color_for_count(n,ref):
    if n<=0: return '#17313B'
    t=clamp(n/max(1,ref))
    if t < 0.14: return '#136F69'
    if t < 0.30: return C['green']
    if t < 0.50: return C['lime']
    if t < 0.70: return C['yellow']
    if t < 0.85: return C['orange']
    return C['red']


def gradient_chart_color(v):
    if v<.11:return '#214E60'
    if v<.26:return '#27A9C5'
    if v<.43:return '#37E7C1'
    if v<.60:return '#8CF05B'
    if v<.72:return '#E8E44A'
    if v<.85:return '#FFAB3B'
    return '#FF5964'


def contribution_days_map(data):
    return {d['date']:max(0,int(d['contributionCount'])) for d in data['days']}


def build_svg(data):
    s=SVG()
    s.add(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="DOLENT developer dashboard with real GitHub contributions">
<defs>
 <linearGradient id="back" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#09131B"/><stop offset="0.55" stop-color="#080C12"/><stop offset="1" stop-color="#120D1B"/></linearGradient>
 <linearGradient id="orb" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#53EAF0"/><stop offset="0.45" stop-color="#1B738D"/><stop offset="1" stop-color="#16343F"/></linearGradient>
 <radialGradient id="glow"><stop stop-color="#2CF6DF" stop-opacity=".27"/><stop offset="1" stop-color="#2CF6DF" stop-opacity="0"/></radialGradient>
 <pattern id="minorGrid" width="23" height="23" patternUnits="userSpaceOnUse"><path d="M23 0H0V23" fill="none" stroke="#244357" stroke-width="0.7" opacity=".31"/></pattern>
 <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 3.5H1440" stroke="#000" stroke-width=".7" opacity=".27"/></pattern>
 <clipPath id="terrainClip"><rect x="374" y="290" width="1046" height="402" rx="9"/></clipPath>
 </defs>
 <rect width="1440" height="1010" fill="url(#back)"/>
 <rect x="17" y="15" width="1406" height="980" rx="14" fill="none" stroke="#356478" stroke-width="1.2"/>
''')
    # top HUD
    s.line(39,71,1400,71,C['border'],1.3)
    s.text(45,49,'DOLENT // CONTROL SYSTEM',24,C['white'],700)
    for i in range(6):s.polygon([(451+i*15,33),(459+i*15,33),(453+i*15,44),(445+i*15,44)],C['cyan'] if i<3 else '#245B66')
    s.text(1022,45,'GITHUB NODE  //  SESSION 001',13,C['soft'])
    s.circle(1365,39,5,C['green']); s.text(1381,45,'ON',13,C['green'],700)
    # sidebar
    s.panel(35,90,312,890,C['purple'])
    s.panel(51,107,281,248,C['cyan'],'#08141A')
    # stylized orbital landscape
    s.circle(192,227,93,'url(#orb)',C['cyan'],1.1)
    s.circle(192,227,103,'none','#1B5365',1)
    for i in range(7):
        yy=158+18*i
        s.path(f'M{111+2*i} {yy} C175 {yy+10} 219 {yy-22} {276-2*i} {yy+4}',C['cyan'],.55,opacity=.45)
    s.polygon([(57,329),(86,306),(101,320),(127,271),(149,287),(184,216),(198,234),(235,194),(272,254),(292,245),(327,330)],'#082C3A','#3CB7CF',1.6)
    s.path('M56 330 L122 288 L143 298 L183 227 L200 246 L237 202 L271 260 L321 329',C['orange'],1.8,opacity=.9)
    s.path('M72 332 L135 303 L184 242 L221 294 L258 273 L316 333',C['cyan'],1.1,opacity=.9)
    for i in range(26):
        x=65+(i*79)%249;y=123+(i*43)%195
        s.circle(x,y,.8,C['white'],extra='opacity="0.55"')
    s.label(57,393,'DOLENT_',C['white'])
    s.text(57,413,'DEVELOPER / SYSTEM ARCHITECT',13,C['soft'])
    s.text(57,432,'AI EXPLORER',13,C['soft'])
    s.line(57,457,326,457,C['border'])
    s.text(57,481,'ACCESS GRANTED  //  MX',12,C['green'])
    s.text(57,520,'/// TECH STACK',16,C['white'],700)
    icons=[('PY','#3DD8CD'),('KT',C['purple']),('TS',C['blue']),('FB',C['orange']),('AI',C['pink'] if 'pink' in C else C['purple']),('GH',C['white']),('DB',C['green']),('<>',C['cyan'])]
    for j,(name,col) in enumerate(icons):
        x=57+(j%4)*67;y=539+(j//4)*63
        s.rect(x,y,52,53,'#0F1924','#2B4B5A',1,8)
        s.rect(x+4,y+4,44,45,'none',col,.8,5)
        s.text(x+26,y+32,name,16,col,700,'text-anchor="middle"')
    s.line(57,675,326,675,C['border'])
    s.text(57,700,'/// FOCUS',16,C['white'],700)
    for i,(t,c) in enumerate([('AI SYSTEMS',C['cyan']),('MOBILE DEVELOPMENT',C['green']),('PRODUCTIVITY TOOLS',C['orange']),('AUTOMATION',C['purple'])]):
        y=732+i*42
        s.path(f'M65 {y-7} L72 {y} L65 {y+7}',c,1.8)
        s.text(85,y+5,t,13,C['soft'])
        s.line(57,y+17,326,y+17,C['line'],.75)
    s.text(58,950,'NODE // ZWORDUP-SUDO',11,C['muted'])
    # content title
    s.text(378,105,'/// PROJECT ARCHIVE',17,C['white'],700)
    s.line(605,100,1397,100,C['border'])
    # project cards
    for x,w,accent,idx,name,subtitle,status,tags in [
        (375,510,C['cyan'],'01','FRYD','AI PRODUCTIVITY SYSTEM','IN DEVELOPMENT',['TypeScript','AI','Productivity']),
        (898,521,C['orange'],'02','HERCULES','ANDROID TRAINING LOG','LOCAL / UNPUBLISHED',['Kotlin','Android','Fitness'])]:
        s.panel(x,113,w,137,accent)
        s.text(x+15,142,idx,15,accent,700)
        s.rect(x+20,158,78,71,'#0D1A24',C['border'],1,7)
        # unique emblem
        if name=='FRYD':
            s.polygon([(x+41,177),(x+59,188),(x+79,171),(x+68,199),(x+60,210),(x+53,195)],accent)
        else:
            s.polygon([(x+47,170),(x+55,170),(x+55,189),(x+72,189),(x+72,170),(x+81,170),(x+81,215),(x+72,215),(x+72,199),(x+55,199),(x+55,215),(x+47,215)],accent)
        s.text(x+119,162,name,28,C['white'],700)
        s.text(x+119,185,subtitle,14,C['soft'])
        xpos=x+119
        for tag in tags:
            ww=len(tag)*7.5+19
            s.rect(xpos,201,ww,24,'#10202B',C['border'],.8,5)
            s.text(xpos+9,217,tag,11,accent)
            xpos+=ww+7
        s.circle(x+w-151,133,3,accent)
        s.text(x+w-140,138,status,11,accent,600)
    # large terrain container
    s.panel(375,266,1044,439,C['cyan'])
    s.text(394,293,'/// ACTIVITY TERRAIN',17,C['white'],700)
    s.text(1149,293,'LAST 12 MONTHS',12,C['soft'])
    s.rect(388,310,1018,379,'url(#minorGrid)')
    # terrain orbital disk / background ticks
    s.add('<g clip-path="url(#terrainClip)">')
    s.add('<ellipse cx="906" cy="627" rx="463" ry="87" stroke="#4A7890" stroke-width="1.2" fill="#08141C" opacity=".85"/>')
    for r in range(6):s.add(f'<ellipse cx="906" cy="627" rx="{140+r*63}" ry="{25+r*11}" stroke="#1B3C4C" stroke-width=".8" fill="none"/>')
    for x in range(410,1410,44):s.line(x,311,x,695,C['line'],.6,.3)
    for y in range(320,695,42):s.line(385,y,1414,y,C['line'],.6,.3)
    # terrain peaks seeded only by actual activity
    dates=sorted(contribution_days_map(data).items())
    weekly=[sum(count for _,count in dates[k:k+7]) for k in range(0,len(dates),7)]
    if not weekly:weekly=[0]*53
    # normalize using high percentile rather than maximum for stable peaks
    sorted_week=sorted(weekly)
    norm=max(1,sorted_week[min(len(sorted_week)-1,int(len(sorted_week)*.92))])
    # spatial gaussian hills using 9 binned weekly activity clusters
    peaks=[]
    for i in range(9):
        a=round(i*len(weekly)/9); b=round((i+1)*len(weekly)/9)
        value=max(weekly[a:b] or [0])
        power=clamp(math.log1p(value)/math.log1p(norm))
        px=-.9+i*1.8/8
        pz=.16+(.62*(.5+.5*math.sin(i*1.7+.6)))
        peaks.append((px,pz,power))
    # render back rows first, front rows last with colored segments
    for zi in range(32, -1, -1):
        z=zi/32
        widthfactor=(.83+.17*(1-z))*math.sqrt(max(0.01,1-(z-.5)**2*2.5))
        vals=[]
        for xi in range(113):
            xx=-widthfactor+(2*widthfactor)*xi/112
            h=0.035+.022*math.sin(xx*14+z*17)**2
            for px,pz,power in peaks:
                h+=.78*power*math.exp(-(((xx-px)/.18)**2+((z-pz)/.28)**2)*1.1)
            h=clamp(h,0,1)
            X=907+xx*483
            Y=629 + (0.5-z)*199 - h*223*(.79+.21*z)
            vals.append((X,Y,h))
        for a,b in zip(vals,vals[1:]):
            lev=(a[2]+b[2])/2
            color=gradient_chart_color(lev)
            s.line(a[0],a[1],b[0],b[1],color,.92,.38+.53*z)
        if zi%4==0:
            for k in range(0,len(vals),7):
                x,y,h=vals[k]
                s.line(x,y,x,y+7,C['cyan'],.55,.2)
    # bright tracking route, stars
    s.path('M520 599 C660 616 668 545 780 578 S941 465 1065 483 S1202 548 1280 520','#DFFDE3',2.4,opacity=.7,extra='stroke-dasharray="7 8"')
    # Label few peaks: activity levels from actual slices
    for i in [1,4,6,8]:
        px,pz,power=peaks[i]
        X=907+px*483
        h=0.05+0.40*power
        Y=629+(0.5-pz)*199-h*145
        Y=clamp(Y,355,615)
        co=gradient_chart_color(.20+.8*power)
        s.circle(X,Y,7,co,'#F8FFFC',2)
        s.circle(X,Y,2,'#F2FCFD')
        s.line(X,Y-8,X,Y-31,co,1.1,.8)
        s.rect(X-27,Y-54,56,21,'#0F2029',co,.7,4)
        s.text(X,Y-39,f'{round(power*100)}%',11,co,600,'text-anchor="middle"')
    # Compass and mini labels
    s.circle(1341,362,42,'none','#477383',1)
    s.path('M1341 335 L1334 380 L1341 368 L1348 380 Z',C['cyan'],.8,'#3DDCE1')
    s.text(1337,308,'N',13,C['cyan'])
    s.text(1340,418,'S',13,C['soft'])
    s.text(1383,367,'E',12,C['soft'])
    s.text(1290,367,'W',12,C['soft'])
    s.add('</g>')
    # telemetry metrics
    metrics=[(375,262,'CONTRIBUTIONS',str(data['total']),C['green']),
             (651,245,'PUBLIC REPOS',str(data['repos']),C['purple']),
             (910,243,'ACTIVE DAYS',str(sum(x['contributionCount']>0 for x in data['days'])),C['orange']),
             (1166,253,'PRIMARY','TypeScript',C['cyan'])]
    for x,w,lab,val,col in metrics:
        s.panel(x,720,w,101,col)
        s.text(x+18,749,lab,13,C['soft'],600)
        s.text(x+18,790,val,26 if len(val)<6 else 21,col,700)
        for j in range(7):
            bh=(j*9+len(val)*5)%25+6
            s.rect(x+w-87+j*9,791-bh,5,bh,col,extra=f'opacity="{.22+j*.08:.2f}"')
    # heatmap panel
    s.panel(375,834,1044,145,C['purple'])
    s.text(394,859,'/// CONTRIBUTION MAP',17,C['white'],700)
    s.text(1141,859,'LESS',12,C['soft'])
    for k in range(1,7):s.rect(1180+k*22,848,16,11,color_for_count(k,6),r=2)
    s.text(1366,859,'MORE',12,C['soft'])
    # weekly calendar aligns Sunday to Saturday
    mapping=contribution_days_map(data)
    parsed=[date.fromisoformat(x) for x in mapping]
    end=max(parsed) if parsed else date.today()
    first=end-timedelta(days=364)
    first-=timedelta(days=(first.weekday()+1)%7)
    n_weeks=math.ceil((end-first).days/7)+1
    sq=12.4; gap=3.9; left=425; top=882
    last_month=None
    # pick 95th percentile for meaningful relative scale
    vals=sorted(mapping.values()); p95=vals[min(len(vals)-1,int(len(vals)*.95))] if vals else 1
    for wi in range(n_weeks):
        ws=first+timedelta(days=wi*7)
        if ws.month!=last_month:
            if wi< n_weeks-1: s.text(left+wi*(sq+gap),878,ws.strftime('%b').upper(),10,C['soft'])
            last_month=ws.month
        for dow in range(7):
            day=ws+timedelta(days=dow)
            if day>end:continue
            val=mapping.get(day.isoformat(),0)
            col=color_for_count(val,p95)
            s.rect(left+wi*(sq+gap),top+dow*13.1,sq,10.8,col,r=2)
    s.text(395,893,'SUN',10,C['muted'])
    s.text(395,919,'TUE',10,C['muted'])
    s.text(395,945,'THU',10,C['muted'])
    # header mode badge explicit labeling synthetic data
    if data['demo']:
        s.rect(765,24,222,25,'#40211D',C['orange'],.85,4)
        s.text(775,41,'PREVIEW: SYNTHETIC DATA',12,C['yellow'],700)
    # footer microtext
    s.text(47,990,'END OF TRANSMISSION //',10,C['muted'])
    s.text(1300,990,'SYS_READY_',10,C['green'],700)
    s.add('<rect x="0" y="0" width="1440" height="1010" fill="url(#scanlines)" opacity=".17" pointer-events="none"/>')
    s.add('</svg>')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text('\n'.join(s.parts),encoding='utf-8')
    print(f'Wrote {OUT} ({OUT.stat().st_size:,} bytes); demo={data["demo"]}, total={data["total"]}')


def main():
    p=argparse.ArgumentParser();p.add_argument('--demo',action='store_true');args=p.parse_args()
    build_svg(demo_data() if args.demo else github_data())
if __name__=='__main__':main()
