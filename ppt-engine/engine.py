#!/usr/bin/env python3
"""Model-directed presentation engine. Layout/creative choices are produced at runtime.
A small PPTX renderer accepts geometry but never picks a topic or layout itself.
"""
import argparse,base64,io,json,os,re,subprocess,sys,tempfile,urllib.request
from pathlib import Path
from PIL import Image,ImageOps
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from layout import repair,validate

API='https://openrouter.ai/api/v1/chat/completions'
MAX_OUTPUT_TOKENS=6500

def chat(messages,model,base_url=API,max_tokens=MAX_OUTPUT_TOKENS,raw_path=None):
    key=os.environ.get('OPENROUTER_API_KEY','')
    if not key:raise RuntimeError('OPENROUTER_API_KEY not set; provide it in the VPS process environment, not on the command line')
    payload={'model':model,'messages':messages,'temperature':.5,'max_tokens':max_tokens}
    # Nemotron spends part of max_tokens on hidden reasoning. A bounded effort
    # leaves room for the complete visual plan instead of truncating its JSON.
    if model=='nvidia/nemotron-3-super-120b-a12b:free':
        payload['reasoning']={'effort':'low'}
    body=json.dumps(payload,ensure_ascii=False).encode()
    req=urllib.request.Request(base_url,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','X-Title':'ProjectArrakis presentation engine'})
    # No implicit paid retry. Persist provider usage even for truncated plans.
    with urllib.request.urlopen(req,timeout=100) as res: ans=json.load(res)
    choice=ans['choices'][0]
    if raw_path:
        Path(raw_path).write_text(json.dumps({'model':model,'message':choice['message'],
            'finish_reason':choice.get('finish_reason'),'usage':ans.get('usage',{})},ensure_ascii=False,indent=2))
    if choice.get('finish_reason')=='length':
        raise ValueError('model output truncated at token cap; increase cap or shorten request (usage in raw response)')
    return choice['message']['content'],ans.get('usage',{})

def parse_json(s):
    if not isinstance(s,str):raise ValueError('model response was not text')
    s=s.strip()
    fence=re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```',s,re.I|re.S)
    if fence:s=fence.group(1).strip()
    if not s.startswith('{') or not s.endswith('}'):
        raise ValueError('model response is not a complete JSON object')
    try:obj=json.loads(s)
    except json.JSONDecodeError:
        # Gemini occasionally writes a duplicate opening quote before a known
        # field, e.g. `," "x":`. Repair ONLY this bounded syntax error;
        # never invent brackets, complete truncated output or alter text values.
        repaired=re.sub(r',\s*"\s*"(?=(?:x|y|w|h|pt|color|bold|align|fill|rounded|focus)"\s*:)',', "',s)
        if repaired==s:raise
        obj=json.loads(repaired)
    if not isinstance(obj,dict):raise ValueError('model response must be a JSON object')
    return obj

def normalize_plan_schema(plan):
    """Unwrap a known Gemini single-key shape drift, without changing design."""
    if 'unsupported_format' in plan:return plan
    import copy
    result=copy.deepcopy(plan)
    if not isinstance(result.get('slides'),list) or not isinstance(result.get('palette'),dict):
        raise ValueError('planner response lacks a complete deck schema')
    for si,slide in enumerate(result['slides']):
        if isinstance(slide.get('background'),dict) and set(slide['background'])=={'fill'}:
            slide['background']=slide['background']['fill']
        normalized=[]
        for ei,e in enumerate(slide.get('elements',[])):
            if 'type' in e:normalized.append(e);continue
            kinds=[k for k in ('text','box','image') if k in e]
            if len(kinds)!=1 or not isinstance(e[kinds[0]],dict):
                raise ValueError(f'unknown element schema slide {si+1} element {ei}')
            item=e[kinds[0]]
            if item.get('type')!=kinds[0]:raise ValueError('nested element type mismatch')
            normalized.append(item)
        slide['elements']=normalized
    return result


def prompt(brief,assets,reference):
    # Compact syntax, not canned content. Planner still chooses story, palette,
    # geometry and imagery. Fewer optional fields keep full JSON inside budget.
    return ("Design a short projector-readable 16:9 deck from this brief. Return ONLY compact JSON, no markdown, explanation, repeated evidence, or verbose intent. "
        "Target under 4200 output tokens; 4-6 slides; <=9 elements per slide; text <=28 words per element. "
        "13.333x7.5in canvas. Required root: palette (name -> six-digit hex), slides. "
        "Each slide: background, elements. Optional intent <=8 words. Each element: "
        "text {type,text,x,y,w,h,pt,color} (optional bold,align); "
        "box {type,x,y,w,h,fill} (optional rounded); "
        "image {type,asset,x,y,w,h} (optional focus). Omitted optional fields use renderer defaults. "
        "Coordinates numeric inches, positive, entirely inside canvas. Array order is layer order. "
        "Creative choices and narrative are yours, not a fixed template. Make distinctive compositions: intentional asymmetry, editorial typography, image-and-number pairings and negative space as the topic suits. Optional fields are optional, not slots to fill. Use different slide layouts when the story calls for them. Keep fonts readable (body >=17pt, sources >=10pt). "
        "Give cards >=0.14in bottom inset for ALL text including captions; leave space for wrapped source notes. "
        "Use only supplied evidence and image asset IDs. Do not infer audited totals, measured growth/trends, or unsupported superlatives from trade projections. "
        "Label estimates on relevant slides; include complete source URLs on a sources slide. Photos are illustrative, not proof of figures. "
        "If requested format isn't PPTX/PDF return {\"unsupported_format\":\"...\"}.\n"
        "BRIEF:\n"+brief+"\nEVIDENCE:\n"+reference+"\nASSETS:\n"+
        json.dumps([{'id':a['id'],'description':a.get('description','')} for a in assets],ensure_ascii=False))


def color(v,palette):
    raw=palette.get(v,v).lstrip('#').upper()
    if not re.fullmatch(r'[A-F0-9]{6}',raw):raise ValueError('invalid color '+str(v))
    return RGBColor.from_string(raw)

def bounds(e):
    vals=[float(e[k]) for k in ('x','y','w','h')]
    x,y,w,h=vals
    if w<=0 or h<=0 or x<0 or y<0 or x+w>13.334 or y+h>7.501:raise ValueError('out-of-slide element '+str(vals))
    return [Inches(v) for v in vals]

def render(plan,assets,out):
    if 'unsupported_format' in plan:raise ValueError('Unsupported target format: '+str(plan['unsupported_format']))
    palette=plan['palette']; slides=plan['slides']
    if not 1<=len(slides)<=16:raise ValueError('invalid slide count')
    pres=Presentation();pres.slide_width=Inches(13.333);pres.slide_height=Inches(7.5)
    for slide in slides:
        sl=pres.slides.add_slide(pres.slide_layouts[6]);bg=sl.background.fill;bg.solid();bg.fore_color.rgb=color(slide['background'],palette)
        for e in slide['elements']:
            typ=e['type'];x,y,w,h=bounds(e)
            if typ=='box':
                sh=sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if e.get('rounded') else MSO_SHAPE.RECTANGLE,x,y,w,h);sh.fill.solid();sh.fill.fore_color.rgb=color(e['fill'],palette);sh.line.fill.background()
                if e.get('rounded'):sh.adjustments[0]=.09
            elif typ=='text':
                pt=float(e['pt']);
                if not 9<=pt<=120:raise ValueError('invalid font size')
                sh=sl.shapes.add_textbox(x,y,w,h);tf=sh.text_frame;tf.clear();tf.word_wrap=True;tf.margin_top=tf.margin_bottom=0;tf.margin_left=tf.margin_right=Inches(.02)
                for i,line in enumerate(e['text'].split('\n')):
                    p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_after=Pt(0);p.line_spacing=1.08;p.alignment={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[e.get('align','left')]
                    r=p.add_run();r.text=line;r.font.name='Inter';r.font.size=Pt(pt);r.font.bold=bool(e.get('bold'));r.font.color.rgb=color(e.get('color','222222'),palette)
            elif typ=='image':
                a=assets.get(e['asset']);
                if not a:raise ValueError('unknown image asset '+str(e['asset']))
                im=Image.open(a['file']).convert('RGB');center=e.get('focus',[.5,.5]);
                if len(center)!=2 or any(not 0<=float(v)<=1 for v in center):raise ValueError('invalid image focus')
                with io.BytesIO() as b:
                    ImageOps.fit(im,(max(100,round(w/914400*145)),max(100,round(h/914400*145))),centering=tuple(center)).save(b,format='JPEG',quality=88);b.seek(0);sl.shapes.add_picture(b,x,y,w,h)
            else:raise ValueError('unknown element type '+str(typ))
    pres.save(out)
    return len(slides)

def preview(pptx,pdf,folder):
    folder.mkdir(exist_ok=True,parents=True)
    cmd=['libreoffice','-env:UserInstallation=file:///tmp/lo-agent-deck-'+str(os.getpid()),'--headless','--convert-to','pdf','--outdir',str(folder),str(pptx)]
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    generated=folder/(pptx.stem+'.pdf');generated.replace(pdf)
    import fitz
    d=fitz.open(pdf)
    images=[]
    for i,p in enumerate(d):
        pix=p.get_pixmap(matrix=fitz.Matrix(.8,.8),alpha=False)
        f=folder/f'slide-{i+1:02}.png';pix.save(f);images.append(f)
    return images

def audit_rendered_text(plan,pdf):
    """PDF text span positions catch output that escapes its model text box/card.

    The PDF renderer is the final viewer; reject questionable assignments rather
    than granting a false pass. Coordinates are normalized to deck inches.
    """
    import fitz
    document=fitz.open(pdf);issues=[]
    for si,page in enumerate(document):
        slide=plan['slides'][si]
        elements=slide['elements']
        cards=[e for e in elements if e.get('type')=='box']
        # PDF extraction can wrap one editable box into several text blocks.
        # Associate each span by its origin and horizontal overlap with the
        # declared text boxes; all matched spans must stay in their geometry.
        spans=[span for block in page.get_text('dict')['blocks'] if block.get('type')==0
               for line in block['lines'] for span in line['spans'] if span['text'].strip()]
        for span in spans:
            x0,y0,x1,y1=[v/72 for v in span['bbox']]
            candidates=[]
            for ei,e in enumerate(elements):
                if e.get('type')!='text':continue
                overlap=max(0,min(x1,e['x']+e['w'])-max(x0,e['x']))
                if not overlap:continue
                # Allow small font ascender/descender offsets from y.
                vertical=max(0,e['y']-.15-y0,y0-e['y']-e['h']-.10)
                candidates.append((vertical,-overlap,ei,e))
            if not candidates:
                issues.append({'slide':si+1,'kind':'unmatched_pdf_text','text':span['text'][:80]});continue
            _,_,ei,e=min(candidates)
            card_candidates=[b for b in cards if b['x']+.04<=e['x'] and e['x']+e['w']<=b['x']+b['w']-.04
                             and b['y']+.04<=e['y'] and e['y']<=b['y']+b['h']]
            if card_candidates:
                card=min(card_candidates,key=lambda b:b['w']*b['h'])
                if y1>card['y']+card['h']-.11:
                    issues.append({'slide':si+1,'element':ei,'kind':'rendered_card_overflow','bottom':round(y1,3),'card_bottom':card['y']+card['h'],'text':span['text'][:80]})
            if y1>7.44 or y0<-.03 or x0<-.03 or x1>13.36:
                issues.append({'slide':si+1,'element':ei,'kind':'rendered_slide_overflow','text':span['text'][:80]})
    return issues

def critic_prompt(plan,images):
    instruction=('Review rendered slides for both objective release defects (overflow, clipping, overlap, missing content, unreadable type, low contrast) AND design sense: clear hierarchy, intentional composition, balanced whitespace, fitting typography, image treatment and a coherent rhythm across slides. A sparse slide with a purposeful focal point is fine; repeated bare text with a half-empty canvas is not. Judge the actual deck against its brief, not personal color taste. Fact verification happens in a later phase; do not certify factual accuracy here. If no objective defect exists return {"approved":true,"issues":[]}. Otherwise return {"approved":false,"issues":[{"slide":1,"problem":"precise visible defect"}],"patches":[{"slide":1,"element":2,"changes":{"x":1.1,"h":1.2}}]}. Slide indices are 1-based, element indices 0-based; only patch an index you can verify in the plan. Patch only exact defective elements. Current plan: '+json.dumps(plan,ensure_ascii=False))
    content=[{'type':'text','text':instruction}]
    for f in images:
        b64=base64.b64encode(f.read_bytes()).decode();content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+b64,'detail':'low'}})
    return content

def apply_patches(plan,patches):
    """Apply only critic-identified changes, never replace the whole plan."""
    import copy
    revised=copy.deepcopy(plan)
    for patch in patches:
        slide=int(patch['slide'])-1;index=int(patch['element'])
        if slide<0 or slide>=len(revised['slides']):continue
        if index<0 or index>=len(revised['slides'][slide]['elements']):continue
        element=revised['slides'][slide]['elements'][index]
        allowed={'x','y','w','h','pt','text','color','fill','focus','align'}
        changes=patch['changes']
        if not changes or set(changes)-allowed:raise ValueError('invalid targeted patch')
        element.update(changes)
    return revised


def targeted_rewrite(plan,issue,model,api_url,raw_path):
    """Ask the planner to shorten ONE text element without changing its facts."""
    from layout import measure
    import copy
    if issue.get('kind')!='text_fit':raise ValueError('only text_fit may be rewritten')
    si,ei=issue['slide'],issue['element']
    element=plan['slides'][si]['elements'][ei]
    before=element['text']
    if element.get('type')!='text':raise ValueError('rewrite target must be text')
    request={'task':'Shorten only this slide text so it fits; preserve numbers, dates, named entities, uncertainty labels and URLs. Do not invent or remove evidence. Return JSON {"text":"..."} only.',
             'slide_intent':plan['slides'][si].get('intent',''),'original_text':before,'box':{k:element[k] for k in ('w','h','pt')},'estimated_lines':issue.get('lines'),'required_height':issue.get('need')}
    raw,usage=chat([{'role':'system','content':'Rewrite a single overflowing slide text element; keep every material fact intact. JSON only.'},{'role':'user','content':json.dumps(request,ensure_ascii=False)}],model,api_url,max_tokens=700,raw_path=raw_path)
    replacement=parse_json(raw).get('text')
    if not isinstance(replacement,str) or not replacement.strip() or len(replacement)>=len(before):raise ValueError('targeted rewrite did not shorten text')
    # Never let a lossy rewrite drop a figure or a source URL.
    import re
    protected=re.findall(r'https?://[^\s<>]+|(?:₹|\$)\s*[\d,]+|\b\d[\d,.]*\s*(?:crore|lakh|%|20\d\d)\b',before,re.I)
    for fact in protected:
        if fact.rstrip('.,;') not in replacement:raise ValueError('targeted rewrite dropped protected fact: '+fact[:45])
    fixed=copy.deepcopy(plan);fixed['slides'][si]['elements'][ei]['text']=replacement
    need,_=measure(replacement,float(element['pt']),float(element['w']),bool(element.get('bold')))
    if need>float(element['h'])+.02:raise ValueError('targeted rewrite still does not fit')
    return fixed,usage


def unsupported_claims(plan):
    # This brief has two distinct trade projections, not longitudinal results.
    pattern=re.compile(r'\b(?:continues? to grow|growing economic impact|economic impact (?:has )?(?:grown|increased)|year[- ]on[- ]year growth|fastest[- ]growing)\b',re.I)
    return [{'slide':si+1,'element':ei,'text':e['text'][:140]}
            for si,s in enumerate(plan['slides']) for ei,e in enumerate(s['elements'])
            if e.get('type')=='text' and pattern.search(e['text'])]

def prepare(plan,out,iteration,model=None,api_url=API,log=None,max_patches=3):
    if getattr(prepare,'enforce_claims',False):
        claims=unsupported_claims(plan)
        if claims:raise ValueError('unsupported growth claim: '+json.dumps(claims))
    fixed,changes,issues=repair(plan)
    patch_count=0
    while issues and model and patch_count<max_patches and all(i['kind']=='text_fit' for i in issues):
        issue=issues[0]
        candidate,usage=targeted_rewrite(fixed,issue,model,api_url,out/f'raw-rewrite-{iteration}-{patch_count}.json')
        if log is not None:log.append({'stage':'rewrite','model':model,'iteration':iteration,'usage':usage,'target':{'slide':issue['slide']+1,'element':issue['element']}})
        fixed,extra,issues=repair(candidate);changes+=extra;patch_count+=1
    (out/f'layout-{iteration}.json').write_text(json.dumps({'changes':changes,'targeted_rewrites':patch_count,'remaining':issues},indent=2))
    if issues:raise ValueError('layout preflight failed: '+json.dumps(issues[:8]))
    return fixed

def run(args):
    prepare.enforce_claims=getattr(args,'enforce_claims',False)
    brief=Path(args.brief).read_text();reference=Path(args.sources).read_text() if args.sources else ''
    manifest=json.loads(Path(args.assets).read_text());assets={a['id']:a for a in manifest}
    for a in assets.values():
        if not Path(a['file']).is_file():raise FileNotFoundError(a['file'])
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    response,usage=chat([{'role':'system','content':'You are a creative lead. Output one JSON plan only. Coordinates are top-left; x+w<=13.333, y+h<=7.5. Keep text boxes large enough for every word. Maximum 8 slides for this brief.'},{'role':'user','content':prompt(brief,manifest,reference)}],args.model,args.api_url,max_tokens=9500 if args.model.endswith(':free') else 7000,raw_path=out/'raw-planner.json')
    plan=normalize_plan_schema(parse_json(response))
    (out/'plan-0.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    log=[{'stage':'planner','model':args.model,'usage':usage}]
    for iteration in range(args.max_revisions+1):
        plan=prepare(plan,out,iteration,args.model,args.api_url,log,max_patches=0 if args.max_revisions==0 else 3)
        (out/f'repaired-plan-{iteration}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
        pptx=out/'deck.pptx';pdf=out/'deck.pdf';render(plan,assets,pptx)
        images=preview(pptx,pdf,out/f'preview-{iteration}')
        rendered_issues=audit_rendered_text(plan,pdf)
        (out/f'render-audit-{iteration}.json').write_text(json.dumps(rendered_issues,indent=2))
        if rendered_issues:
            (out/'run-log.json').write_text(json.dumps({'iterations':log,'visual_qa':'FAILED: rendered text escaped card/slide','rendered_issues':rendered_issues},indent=2))
            raise ValueError('rendered text QA failed: '+json.dumps(rendered_issues[:8]))
        if not args.vision_model:
            (out/'run-log.json').write_text(json.dumps({'iterations':log,'visual_qa':'UNVERIFIED: no vision model supplied; human review required'},indent=2))
            print('Generated but visually unverified; supply --vision-model to run critic loop.');return 2
        raw,usage=chat([{'role':'system','content':'You are a rigorous visual presentation critic. Return strict JSON. Diagnose actual rendered pages and offer only targeted element patches.'},{'role':'user','content':critic_prompt(plan,images)}],args.vision_model,args.api_url,max_tokens=800,raw_path=out/f'raw-critic-{iteration}.json')
        result=parse_json(raw);log.append({'stage':'critic','model':args.vision_model,'iteration':iteration,'usage':usage,'issues':result.get('issues',[])})
        (out/f'critique-{iteration}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('approved') is True:
            (out/'run-log.json').write_text(json.dumps({'iterations':log,'visual_qa':'model-inspected all slide previews; review PDF as final viewer check'},indent=2));print('Approved',pptx,pdf);return 0
        if iteration>=args.max_revisions:break
        if not result.get('patches'):raise ValueError('critic rejected without targeted patches')
        plan=apply_patches(plan,result['patches']);(out/f'plan-{iteration+1}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    (out/'run-log.json').write_text(json.dumps({'iterations':log,'visual_qa':'FAILED: unresolved critic issues'},indent=2))
    print('Critic did not approve; files are drafts, not deliverable',file=sys.stderr);return 3

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--brief',required=True);ap.add_argument('--assets',required=True);ap.add_argument('--sources');ap.add_argument('--output',required=True);ap.add_argument('--model',default='google/gemini-2.5-flash');ap.add_argument('--vision-model',default='google/gemini-2.5-flash');ap.add_argument('--api-url',default=API,help='OpenAI-compatible test endpoint override; keep default on VPS');ap.add_argument('--max-revisions',type=int,default=2);ap.add_argument('--enforce-claims',action='store_true',help='Opt-in factual trend guard; fact review is a separate phase')
    try:sys.exit(run(ap.parse_args()))
    except Exception as exc: print('ERROR:',exc,file=sys.stderr);sys.exit(1)
