"""Task-local source-less FLS livery encoder; mirrors upstream livery_codec.cpp.

Restricted to source-less authoring projects. Original .3so is never rewritten.
Native output must pass independent FH6Preview readback before installation.
"""
import base64
import gzip
import json
import math
from pathlib import Path
import re
import struct
import sys
from datetime import datetime, timezone, timedelta

WORKSPACE = Path(__file__).resolve().parents[1]

I = (1., 0., 0., 0., 1., 0.)
SLOT_ROT = (0., 0., 0., 180., 90., -90., 90., 0., 0., 180., 0.)
EMPTY_ROT = (0., 0., 0., 0., 180., 90., -90., 90., 0., 0., 180.)

def mul(a, b):
    return (a[0]*b[0]+a[1]*b[3], a[0]*b[1]+a[1]*b[4], a[0]*b[2]+a[1]*b[5]+a[2],
            a[3]*b[0]+a[4]*b[3], a[3]*b[1]+a[4]*b[4], a[3]*b[2]+a[4]*b[5]+a[5])

def mat(t):
    r=math.radians(t.get('rotation',0)); c=math.cos(r); s=math.sin(r)
    sx=t.get('scale_x',1); sy=t.get('scale_y',1); k=t.get('skew',0)
    return (c*sx,(c*k-s)*sy,t.get('x',0),s*sx,(s*k+c)*sy,t.get('y',0))

def dec(a):
    x,y=a[2],a[5]; sx=math.hypot(a[0],a[3])
    if sx<1e-8: return x,y,0.,math.hypot(a[1],a[4]),0.,0.
    if a[0]*a[4]-a[1]*a[3]<0: sx=-sx;r=math.atan2(-a[3],-a[0])
    else: r=math.atan2(a[3],a[0])
    c=math.cos(r);s=math.sin(r);m01=c*a[1]+s*a[4];sy=-s*a[1]+c*a[4]
    return x,y,sx,sy,math.degrees(r)%360,m01/sy if abs(sy)>1e-8 else 0.

def attach(n,parent=I):
    n['_world']=mul(parent,mat(n.get('transform',{})))
    for child in n.get('children',[]):attach(child,n['_world'])

def leaves(n):
    if n.get('kind')=='shape':return [n]
    if not n.get('visible',True):return []
    return [s for c in n.get('children',[]) for s in leaves(c)]

def entries(n):
    out=[]
    for c in n.get('children',[]):
        if c.get('kind')=='shape':out.append(c)
        elif c.get('kind')=='group' and c.get('visible',True) and leaves(c):
            kids=entries(c)
            out.append(kids[0] if len(kids)==1 else c)
    return out

def depth(n):
    if n['kind']!='group':return 1
    kids=entries(n)
    return 1+depth(kids[-1]) if kids and kids[-1]['kind']=='group' else 1

def header(kids,counted=False,mask=False):
    assert 0<len(kids)<=65535
    bitmap=bytearray((len(kids)+7)//8)
    for i,c in enumerate(kids):
        if c['kind']=='group':bitmap[i//8]|=1<<(i%8)
    return (bytes([0x60 if mask else 0x20]) if counted else b'')+struct.pack('<HH',len(kids),len(bitmap))+bytes(2)+bitmap

def origin(n,adj):
    pts=[]
    for s in leaves(n):
        a=mul(adj,s['_world']);v=s['visual'];hx=hy=64.
        if v['kind']=='raster':
            w=max(1,v.get('width',256));h=max(1,v.get('height',256));side=max(w,h)
            hx=64*w/side;hy=64*h/side
        for x,y in [(-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy)]:
            pts.append((a[0]*x+a[1]*y+a[2],a[3]*x+a[4]*y+a[5]))
    return ((min(x for x,y in pts)+max(x for x,y in pts))/2,
            (min(y for x,y in pts)+max(y for x,y in pts))/2)

def artwork(n,adj,lead,bare):
    v=n['visual'];rid=v['shape_id'] if v['kind']=='vector' else 0x8000|v['raster_id']
    assert 0<rid<65536
    marker=bytes.fromhex(n.get('debug',{}).get('marker',''))
    known=marker in (b'\x02',b'\x00\x02',b'\x01\x02')
    if known and len(marker)==2:lead=marker[0]
    if known:bare=len(marker)==1
    x,y,sx,sy,r,k=dec(mul(adj,n['_world']))
    values=(r,x,y,sx,sy,k)
    assert all(math.isfinite(x) for x in values)
    return (b'' if bare else bytes([lead]))+b'\x02'+struct.pack('<H6f4B',rid,*values,*n['color'])

def transform_marker(marker):
    if not marker:return marker
    if marker[0] in (0,1):return marker[:1]
    return marker[:-1]+b'\x01' if marker[-1]==3 else marker

def sequence(kids,adj,parent_origin=(0.,0.),section=False):
    out=bytearray();prev_group=False;prev_depth=0;prev_mask=False;had=False
    parent_mask=not section and all(s.get('mask',False) for n in kids for s in leaves(n))
    for child in kids:
        if child['kind']=='group':
            marker=(b'\x00'+b'\x01'*max(1,prev_depth)+b'\x03' if prev_group else
                    (b'\x00\x03' if had else (b'' if section else b'\x01')))
            if prev_mask and marker and marker[0]==0:marker=b'\x01'+marker[1:]
            data,prev_mask=group(child,adj,parent_origin,marker,parent_mask)
            out.extend(data);prev_group=True;prev_depth=depth(child)
        else:
            lead=1 if prev_mask or (not section and (not had or parent_mask)) else 0
            # Group-contained artwork always carries a two-byte marker.
            shape=dict(child)
            if not section:
                shape['debug']=dict(child.get('debug',{}))
                if shape['debug'].get('marker')=='02':shape['debug']['marker']=''
            local=mul((1.,0.,-parent_origin[0],0.,1.,-parent_origin[1]),adj)
            out.extend(artwork(shape,local,lead,section and not had))
            prev_group=False;prev_depth=0;prev_mask=parent_mask or child.get('mask',False)
        had=True
    return bytes(out),prev_mask

def group(n,adj,parent_origin,marker,parent_mask):
    kids=entries(n);o=origin(n,adj);mask=all(s.get('mask',False) for s in leaves(n))
    out=transform_marker(marker)+struct.pack('<4f',o[0]-parent_origin[0],o[1]-parent_origin[1],1.,0.)
    out+=header(kids,True,mask)
    data,prev=sequence(kids,adj,o,False)
    return out+data,prev or parent_mask

def gyvl(j):
    body=bytearray();counts=[]
    slots={n['livery_section_slot']:n for n in j['root']['children'] if n.get('is_livery_section')}
    assert set(slots)==set(range(11))
    count=[len(leaves(slots[i])) for i in range(11)]
    last=max(i for i in range(11) if count[i])
    for i in range(11):
        n=slots[i];num=count[i];assert num<=(3000 if i in (2,3,4) else 1000)
        counts.append(num)
        if not num:
            empty=bytes(8)+struct.pack('<2f',1.,EMPTY_ROT[i])+bytes(7)
            body.extend(empty[17:] if i==last+1 else empty);continue
        kids=entries(n);adj=(-1.,0.,0.,0.,-1.,0.) if i==5 else I
        body.extend(header(kids));data,prev=sequence(kids,adj,section=True);body.extend(data)
        terminal_mask=leaves(n)[-1].get('mask',False)
        nested=kids[-1]['kind']=='group' and depth(kids[-1])>1
        grouped=any(k['kind']=='group' for k in kids)
        if nested and i==10:body.extend(bytes([int(terminal_mask)]))
        elif grouped or i<10:body.extend(bytes([int(terminal_mask)])+bytes(8)+struct.pack('<2f',1.,SLOT_ROT[i])+b'\0')
        else:body.extend(bytes([int(terminal_mask)]))
    return b'gyvl'+bytes(8)+struct.pack('<f',1.)+bytes(5)+body,counts

def descriptors(j):
    source=(WORKSPACE/'assets/material_hashes.h').read_text('utf8')
    values={k:int(v,16) for k,v in re.findall(r'quint64\s+(k\w+)\s*=\s*(0x[0-9A-Fa-f]+)ULL',source)}
    def array(name):
        raw=re.search(r'\b'+name+r'\s*=\s*\{(.*?)\};',source,re.S).group(1)
        result=[]
        for token in raw.split(','):
            token=token.strip()
            if not token:continue
            if token.startswith('0x'):result.append(int(token.removesuffix('ULL'),16))
            elif '[' in token:
                a,index=token[:-1].split('[');result.append(array(a)[int(index)])
            else:result.append(values[token])
        return result
    materials={int(m['material_hash'],16):m for m in j['livery_paint']['materials']}
    panels=array('kLiveryPanels');hashes=list(dict.fromkeys(array('kLiveryMaterials')+list(materials)+panels))
    out=bytearray(b'yrvl\0\x02'+struct.pack('<H',len(hashes))+bytes(6))
    for h in hashes:
        m=materials.get(h,{})
        if h in array('kFrontWheelPaint')+array('kRearWheelPaint') and not any([m.get('finish',0),m.get('primary',{}).get('enabled'),m.get('secondary',{}).get('enabled')]):
            for fallback in array('kWheelPaintGroups'):
                candidate=materials.get(fallback,{})
                if candidate.get('finish',0) or candidate.get('primary',{}).get('enabled') or candidate.get('secondary',{}).get('enabled'):m=candidate;break
        p=m.get('primary',{});s=m.get('secondary',{});finish=m.get('finish',0)
        if h==values['kWindowGlass']:finish=0
        elif not finish and (p.get('enabled') or s.get('enabled')):finish=1
        out.extend(struct.pack('<QB?4B?4BII',h,2,p.get('enabled',False),*p.get('bgra',[0]*4),s.get('enabled',False),*s.get('bgra',[0]*4),m.get('manufacturer_selector',0xffffffff if h in panels else 0),finish))
    out.extend(struct.pack('<I',len(panels))+b''.join(struct.pack('<Q',h) for h in panels))
    return bytes(out)
