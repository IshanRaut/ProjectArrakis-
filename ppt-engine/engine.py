#!/usr/bin/env python3
"""Model-directed presentation engine. Layout/creative choices are produced at runtime.
A small PPTX renderer accepts geometry but never picks a topic or layout itself.
"""
import argparse,base64,io,json,os,re,subprocess,sys,tempfile,time,urllib.request
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
    body=json.dumps({'model':model,'messages':messages,'temperature':.5,'max_tokens':max_tokens},ensure_ascii=False).encode()
    req=urllib.request.Request(base_url,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','X-Title':'ProjectArrakis presentation engine'})
    last=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=100) as res: ans=json.load(res)
            if raw_path:
                # Never persist request headers, environment, or API keys.
                Path(raw_path).write_text(json.dumps({'model':model,'message':ans['choices'][0]['message'],'finish_reason':ans['choices'][0].get('finish_reason'),'usage':ans.get('usage',{})},ensure_ascii=False,indent=2))
            return ans['choices'][0]['message']['content'],ans.get('usage',{})
        except Exception as exc:
            last=exc
            if attempt<2:time.sleep(1.5*(attempt+1))
    raise RuntimeError(f'Model call failed after retries: {last}')

def parse_json(s):
    if not isinstance(s,str):raise ValueError('model response was not text')
    s=re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$','',s.strip())
    try:return json.loads(s)
    except json.JSONDecodeError:
        # Bounded salvage: drop explanatory prefixes/suffixes around a complete
        # object; never invent closing braces or silently change content.
        dec=json.JSONDecoder()
        for match in list(re.finditer(r'\{',s))[:5]:
            try:
                obj,end=dec.raw_decode(s[match.start():])
                if isinstance(obj,dict):return obj
            except json.JSONDecodeError:continue
        raise


def prompt(brief,assets,reference):
    return '''You are a presentation creative director. Think through purpose, audience, story, visual metaphor, source reliability, and the reference design. You decide everything creative at runtime. The renderer only implements your design geometry. Respond with ONE JSON object, no markdown.

Canvas is 13.333 by 7.5 inches. You MUST include keys: rationale (string), palette (object of color names -> six-digit hex strings), slides (array, 4-12). Each slide has background (palette name or hex), intent (string), elements (array). Each element is ONE of:
- {"type":"text","text":"...","x":number,"y":number,"w":number,"h":number,"pt":number,"color":"palette key or hex","bold":bool,"align":"left|center|right"}
- {"type":"box","x":number,"y":number,"w":number,"h":number,"fill":"palette key or hex","rounded":bool}
- {"type":"image","asset":"asset ID from manifest","x":number,"y":number,"w":number,"h":number,"focus":[0.5,0.5]}
Geometry must fit canvas. Layer order is array order. Keep text editable, give whitespace and hierarchy. No inherited placeholders or stale navigation. Build a topic-appropriate deck, not a rigid template clone. Use real assets ONLY from the manifest; do not invent image URLs or imply that an illustrative image documents a number. Use supplied evidence only: do not invent figures, quotations, or source URLs. Put material source labels and uncertainties on slides. A sources page should carry URLs. Avoid minuscule type (body >=17pt, sources >=10pt). If brief asks another output format, stop and return {"unsupported_format":"..."}; this engine only produces PPTX and PDF.

USER BRIEF:\n'''+brief+'\n\nEVIDENCE / SOURCES:\n'+reference+'\n\nIMAGE MANIFEST:\n'+json.dumps(assets,ensure_ascii=False)

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

def critic_prompt(plan,images):
    instruction=('Inspect all rendered slides for OBJECTIVE release defects only: text overflow or overlap, clipped or missing content, unreadable text at presentation size, invalid/unsupported numbers or citations, and severe contrast failure. Cropping of stock photography is expected and not itself a failure. Do not fail for subjective taste, hierarchy, color preference, full URLs that are readable in the PDF, or ordinary design tradeoffs. If no objective defect exists return {"approved":true,"issues":[]}. Otherwise return {"approved":false,"issues":[{"slide":1,"problem":"precise visible defect"}],"patches":[{"slide":1,"element":2,"changes":{"x":1.1,"h":1.2}}]}. Slide indices are 1-based, element indices 0-based; only patch an index you can verify in the plan. Patch only exact defective elements. Current plan: '+json.dumps(plan,ensure_ascii=False))
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


def prepare(plan,out,iteration,model=None,api_url=API,log=None,max_patches=3):
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
    brief=Path(args.brief).read_text();reference=Path(args.sources).read_text() if args.sources else ''
    manifest=json.loads(Path(args.assets).read_text());assets={a['id']:a for a in manifest}
    for a in assets.values():
        if not Path(a['file']).is_file():raise FileNotFoundError(a['file'])
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    response,usage=chat([{'role':'system','content':'You are a creative lead. Output one JSON plan only. Coordinates are top-left; x+w<=13.333, y+h<=7.5. Keep text boxes large enough for every word. Maximum 8 slides for this brief.'},{'role':'user','content':prompt(brief,manifest,reference)}],args.model,args.api_url,max_tokens=12000,raw_path=out/'raw-planner.json')
    plan=parse_json(response);(out/'plan-0.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    log=[{'stage':'planner','model':args.model,'usage':usage}]
    for iteration in range(args.max_revisions+1):
        plan=prepare(plan,out,iteration,args.model,args.api_url,log,max_patches=3)
        (out/f'repaired-plan-{iteration}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
        pptx=out/'deck.pptx';pdf=out/'deck.pdf';render(plan,assets,pptx)
        images=preview(pptx,pdf,out/f'preview-{iteration}')
        if not args.vision_model:
            (out/'run-log.json').write_text(json.dumps({'iterations':log,'visual_qa':'UNVERIFIED: no vision model supplied; human review required'},indent=2))
            print('Generated but visually unverified; supply --vision-model to run critic loop.');return 2
        raw,usage=chat([{'role':'system','content':'You are a rigorous visual presentation critic. Return strict JSON. Diagnose actual rendered pages and offer only targeted element patches.'},{'role':'user','content':critic_prompt(plan,images)}],args.vision_model,args.api_url,max_tokens=3500,raw_path=out/f'raw-critic-{iteration}.json')
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
    ap=argparse.ArgumentParser();ap.add_argument('--brief',required=True);ap.add_argument('--assets',required=True);ap.add_argument('--sources');ap.add_argument('--output',required=True);ap.add_argument('--model',default='google/gemini-2.5-flash');ap.add_argument('--vision-model',default='google/gemini-2.5-flash');ap.add_argument('--api-url',default=API,help='OpenAI-compatible test endpoint override; keep default on VPS');ap.add_argument('--max-revisions',type=int,default=2)
    try:sys.exit(run(ap.parse_args()))
    except Exception as exc: print('ERROR:',exc,file=sys.stderr);sys.exit(1)
