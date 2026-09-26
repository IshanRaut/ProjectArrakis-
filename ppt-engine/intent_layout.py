"""Layout archetypes. Models supply content/visual intent, never coordinates.

A layout is accepted only after measured text fits every allocated region; no
truncation or silently clipped text. All elements remain native PPTX objects.
"""
from layout import measure,repair,W,H

ARCHETYPES=('title_hero','big_stat','card_grid','split_image_text','quote','timeline','closing')


def _text(value,x,y,w,h,pt,color,bold=False,align='left',min_pt=14):
    value=str(value or '').strip()
    if not value:return None
    for size in range(int(pt),int(min_pt)-1,-1):
        required,_=measure(value,size,w,bold)
        if required<=h-.035:
            return dict(type='text',text=value,x=x,y=y,w=w,h=h,pt=size,color=color,bold=bold,align=align)
    raise ValueError(f'text cannot fit ({len(value)} chars, {w:.2f}x{h:.2f}in): {value[:80]}')


def _box(x,y,w,h,fill):return dict(type='box',x=x,y=y,w=w,h=h,fill=fill,rounded=True)
def _img(asset,x,y,w,h):return dict(type='image',asset=asset,x=x,y=y,w=w,h=h)
def _add(elements,*items):elements.extend(e for e in items if e is not None)


def _palette(entries):
    if isinstance(entries,dict):return entries
    if not isinstance(entries,list):raise ValueError('palette must be named entries')
    palette={}
    for item in entries:
        if not isinstance(item,dict) or not item.get('name') or not item.get('hex'):
            raise ValueError('invalid palette entry')
        palette[item['name']]=item['hex']
    return palette


def compose(intent,assets):
    """Convert the planner's semantic slide list to the renderer's geometry."""
    palette=_palette(intent.get('palette'))
    if not palette:raise ValueError('palette empty')
    slides=intent.get('slides')
    if not isinstance(slides,list) or not 1<=len(slides)<=8:raise ValueError('intent slide count must be 1..8')
    out={'palette':palette,'slides':[]}
    for si,s in enumerate(slides):
        if not isinstance(s,dict):raise ValueError(f'slide {si+1} must be an object')
        pattern=s.get('archetype')
        if pattern not in ARCHETYPES:raise ValueError(f'unknown archetype slide {si+1}: {pattern}')
        title=s.get('title') or ''
        subtitle=s.get('subtitle') or ''
        body=s.get('body') or ''
        quote=s.get('quote') or ''
        source=s.get('source') or ''
        items=s.get('items') or []
        if not isinstance(items,list):raise ValueError('items must be list')
        if any(not isinstance(item,dict) for item in items):raise ValueError('each item must be object')
        image=s.get('image_asset')
        if image and image not in assets:raise ValueError(f'unknown image asset: {image}')
        bg=s.get('background') or 'FFF9E9'
        ink=s.get('ink') or '222222'
        accent=s.get('accent') or 'A30000'
        card=s.get('card') or 'FFF4C9'
        e=[]
        if pattern=='title_hero':
            if image:
                _add(e,_img(image,7.0,.55,5.75,6.4))
                text_w=5.9
            else:text_w=11.7
            _add(e,_text(title,.7,1.05,text_w,2.05,54,ink,True,min_pt=30),
                 _text(subtitle,.72,3.4,text_w,1.1,26,accent,min_pt=18),
                 _text(body,.72,4.8,text_w,1.35,20,ink,min_pt=15))
        elif pattern=='big_stat':
            if not items or not items[0].get('value'):raise ValueError('big_stat needs a value')
            _add(e,_text(title,.7,.55,11.8,.8,38,ink,True,min_pt=26),
                 _box(.7,1.65,7.0,4.7,card),
                 _text(items[0]['value'],1.02,2.05,6.35,1.7,58,accent,True,min_pt=34),
                 _text(items[0].get('heading'),1.02,3.75,6.35,1.05,26,ink,True,min_pt=18),
                 _text(body or items[0].get('text'),1.02,4.9,6.35,1.12,19,ink,min_pt=15))
            if image:_add(e,_img(image,8.0,1.65,4.65,4.7))
            elif subtitle:
                # A half-empty right column needs a visual anchor: use a
                # deliberate rail/card tied to the main statistic, never
                # detached free-floating prose.
                _add(e,_box(8.0,2.65,4.55,1.85,card),
                     _box(8.0,2.65,.14,1.85,accent),
                     _text(subtitle,8.36,2.97,3.85,1.12,23,ink,True,min_pt=17))
        elif pattern=='card_grid':
            n=len(items)
            if not 2<=n<=4:raise ValueError('card_grid needs 2-4 cards')
            _add(e,_text(title,.65,.4,12.0,.85,37,ink,True,min_pt=25))
            cols=2 if n==4 else n
            rows=2 if n==4 else 1
            w=(11.95-(cols-1)*.3)/cols
            h=4.65 if rows==1 else 2.15
            for k,item in enumerate(items):
                col=k%cols;row=k//cols;x=.7+col*(w+.3);y=1.55+row*(h+.32)
                _add(e,_box(x,y,w,h,card))
                # A balanced vertical stack leaves room for the stat to breathe
                # while avoiding a tiny cluster in the top quarter of a tall
                # card. Measured text may still shrink inside each zone.
                if rows==1:
                    value_y,head_y,copy_y=y+.45,y+1.92,y+3.02
                    value_h,head_h,copy_h=.93,.85,1.05
                else:
                    value_y,head_y,copy_y=y+.18,y+.84,y+1.42
                    value_h,head_h,copy_h=.59,.49,.53
                if item.get('value'):
                    _add(e,_text(item['value'],x+.23,value_y,w-.46,value_h,38,accent,True,min_pt=24))
                else:head_y=y+(.55 if rows==1 else .25)
                _add(e,_text(item.get('heading'),x+.23,head_y,w-.46,head_h,23,ink,True,min_pt=17))
                _add(e,_text(item.get('text'),x+.23,copy_y,w-.46,copy_h,17,ink,min_pt=14))
        elif pattern=='split_image_text':
            if not image:raise ValueError('split_image_text needs image asset')
            side=s.get('image_side') or 'right'
            if side not in ('left','right'):raise ValueError('image_side must be left/right')
            ix,tx=(.65,7.0) if side=='left' else (7.0,.7)
            _add(e,_img(image,ix,.55,5.65,6.35),
                 _text(title,tx,.75,5.65,1.30,39,ink,True,min_pt=24),
                 _text(subtitle,tx,2.25,5.65,.9,24,accent,min_pt=17),
                 _text(body,tx,3.25,5.65,2.85,22,ink,min_pt=15))
        elif pattern=='quote':
            _add(e,_text(title,.75,.6,11.8,.8,34,accent,True,min_pt=24),
                 _text('“'+quote+'”',1.0,1.65,11.25,3.65,39,ink,True,'center',min_pt=23),
                 _text(subtitle,1.0,5.6,11.25,.7,20,accent,align='center',min_pt=15))
        elif pattern=='timeline':
            n=len(items)
            if not 2<=n<=4:raise ValueError('timeline needs 2-4 steps')
            _add(e,_text(title,.7,.5,11.8,.85,38,ink,True,min_pt=26))
            h=4.75/n
            for k,item in enumerate(items):
                y=1.55+k*h
                _add(e,_box(.8,y,.5,.5,accent),
                     _text(item.get('heading'),1.6,y-.02,10.6,.52,23,ink,True,min_pt=17),
                     _text(item.get('text'),1.6,y+.53,10.6,min(.63,h-.59),17,ink,min_pt=14))
        elif pattern=='closing':
            _add(e,_text(title,.7,.55,11.8,.85,39,ink,True,min_pt=27))
            # A sources page may use up to three long entries; each is given
            # a full-width, generous band with measurable height.
            if items:
                if len(items)>3:raise ValueError('closing supports at most 3 source items')
                band=4.8/len(items)
                for k,item in enumerate(items):
                    text='\n'.join(filter(None,[item.get('heading'),item.get('text')]))
                    _add(e,_text(text,.8,1.65+k*band,11.75,band-.18,18,ink,min_pt=10))
            else:_add(e,_text(body,.8,2.0,11.75,3.65,29,ink,min_pt=18))
        if source:
            # Source note is outside cards and images. Strictly one line;
            # if it cannot fit, the model must shorten it, never crop it.
            _add(e,_text(source,.72,7.04,11.85,.38,10,ink,min_pt=10))
        if not e:raise ValueError(f'empty slide {si+1}')
        out['slides'].append({'background':bg,'intent':pattern,'elements':e})
    fixed,changes,issues=repair(out)
    if issues:raise ValueError('composed layout invalid: '+str(issues[:8]))
    return fixed,changes
