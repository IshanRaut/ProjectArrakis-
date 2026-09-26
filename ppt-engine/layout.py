"""Deterministic layout preflight for native editable slide objects.

Measure text with the installed font and reserve comfortable height before
allowing PPTX rendering. Repair only faulty elements; keep content intact.
"""
import copy
import re
from functools import lru_cache
from PIL import ImageFont

W,H=13.333,7.5
DPI=120

@lru_cache(maxsize=128)
def font_for(pt,bold=False):
    paths=('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
           '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')
    for path in paths:
        try:return ImageFont.truetype(path,max(10,round(pt*DPI/72)))
        except OSError:pass
    raise RuntimeError('Install a measurable TrueType font before rendering')


def plain(s):
    return re.sub(r'<[^>]+>','',str(s)).replace('&amp;','&').replace('&nbsp;',' ')


def measure(text,pt,width,bold=False):
    font=font_for(pt,bold)
    maxpx=max(1,(width-.14)*DPI)
    lines=[]
    for paragraph in plain(text).split('\n'):
        if not paragraph.strip():lines.append('');continue
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if font.getlength(candidate)<=maxpx:
                line=candidate;continue
            if line:lines.append(line);line=''
            if font.getlength(word)<=maxpx:line=word;continue
            for char in word:
                if line and font.getlength(line+char)>maxpx:
                    lines.append(line);line=''
                line+=char
        lines.append(line)
    # PowerPoint/LibreOffice line spacing and font substitution need headroom.
    linepx=pt*DPI/72*1.33
    return len(lines)*linepx/DPI+.12,len(lines)


def intersection(a,b):
    l=max(a['x'],b['x']);r=min(a['x']+a['w'],b['x']+b['w'])
    t=max(a['y'],b['y']);bot=min(a['y']+a['h'],b['y']+b['h'])
    return max(0,r-l)*max(0,bot-t)


def validate(plan):
    issues=[]
    for si,slide in enumerate(plan['slides']):
        texts=[]
        for ei,e in enumerate(slide['elements']):
            x,y,w,h=(float(e.get(k,0)) for k in ('x','y','w','h'))
            if min(w,h)<=0 or x<0 or y<0 or x+w>W+.001 or y+h>H+.001:
                issues.append({'slide':si,'element':ei,'kind':'bounds','detail':'element outside canvas'});continue
            if e.get('type')!='text':continue
            need,lines=measure(e['text'],float(e['pt']),w,bool(e.get('bold')))
            if need>h+.02:issues.append({'slide':si,'element':ei,'kind':'text_fit','need':round(need,3),'have':h,'lines':lines})
            for oj,other in texts:
                overlap=intersection(e,other)
                if overlap>.025:issues.append({'slide':si,'element':ei,'other':oj,'kind':'text_overlap','area':round(overlap,3)})
            texts.append((ei,e))
    return issues


def repair(plan,passes=5):
    """Local, element-specific repairs, not another full-plan rewrite."""
    p=copy.deepcopy(plan);changes=[]
    for _ in range(passes):
        faults=validate(p)
        if not faults:break
        progress=False
        for fault in faults:
            si,ei=fault['slide'],fault['element'];e=p['slides'][si]['elements'][ei]
            before=(e.get('x'),e.get('y'),e.get('w'),e.get('h'),e.get('pt'))
            if fault['kind']=='bounds':
                e['x']=max(.08,min(float(e['x']),W-.3));e['y']=max(.08,min(float(e['y']),H-.25))
                e['w']=max(.2,min(float(e['w']),W-e['x']-.04));e['h']=max(.2,min(float(e['h']),H-e['y']-.04))
            elif fault['kind']=='text_fit':
                available=H-float(e['y'])-.08
                # Expand a box into genuinely unoccupied vertical space first.
                desired=min(available,float(fault['need'])+.08)
                others=[o for j,o in enumerate(p['slides'][si]['elements']) if j!=ei and o.get('type')=='text' and max(e['x'],o['x'])<min(e['x']+e['w'],o['x']+o['w'])]
                ceiling=min([o['y']-e['y']-.1 for o in others if o['y']>e['y']+.01] or [available])
                e['h']=max(float(e['h']),min(desired,ceiling))
                need,_=measure(e['text'],float(e['pt']),float(e['w']),bool(e.get('bold')))
                if need>e['h']+.02:
                    floor=10 if ('source' in e['text'].lower() or 'http' in e['text'].lower()) else 15
                    pt=float(e['pt'])
                    while pt>floor and need>e['h']+.02:
                        pt=max(floor,pt-1);need,_=measure(e['text'],pt,float(e['w']),bool(e.get('bold')))
                    e['pt']=pt
            elif fault['kind']=='text_overlap':
                other=p['slides'][si]['elements'][fault['other']]
                # Try to move the lower text down, if there is canvas space.
                upper,lower=(e,other) if e['y']<=other['y'] else (other,e)
                new_y=upper['y']+upper['h']+.12
                if new_y+lower['h']<=H-.08:lower['y']=new_y
                else:
                    upper['h']=max(.2,lower['y']-upper['y']-.12)
            after=(e.get('x'),e.get('y'),e.get('w'),e.get('h'),e.get('pt'))
            if before!=after:changes.append({'slide':si+1,'element':ei,'kind':fault['kind'],'before':before,'after':after});progress=True
        if not progress:break
    return p,changes,validate(p)
