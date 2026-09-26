import unittest
from layout import measure,validate,repair

class LayoutTests(unittest.TestCase):
    def test_color_and_slide_limit(self):
        from layout import normalize_colors
        p={'palette':{'dark':'11223380'},'slides':[{'background':'dark','elements':[{'type':'box','x':1,'y':1,'w':1,'h':1,'fill':'#00000080'}]}]}
        q=normalize_colors(p)
        self.assertEqual(q['palette']['dark'],'112233')
        self.assertEqual(q['slides'][0]['elements'][0]['fill'],'000000')
        p['slides']*=9
        self.assertIn('slide_count',{i['kind'] for i in validate(p)})
    def test_measure_multiline_and_markup(self):
        a,_=measure('short',32,4)
        b,n=measure('<b>Long source label</b> ' * 8,32,4)
        self.assertGreater(b,a);self.assertGreater(n,1)
    def test_micro_nudge_preserves_text(self):
        from layout import repair,validate
        p={'slides':[{'elements':[{'type':'text','text':'A short source label','x':1,'y':1,'w':5,'h':.37,'pt':15}]}]}
        fixed,changes,issues=repair(p)
        self.assertFalse(issues)
        self.assertEqual(fixed['slides'][0]['elements'][0]['text'],'A short source label')
        self.assertTrue(any(c['kind']=='micro_text_fit_nudge' for c in changes))
    def test_targeted_repair(self):
        p={'slides':[{'elements':[{'type':'text','text':'A long headline that cannot fit in a tiny box','x':1,'y':1,'w':4,'h':.35,'pt':40},{'type':'text','text':'Second','x':1,'y':4,'w':3,'h':.8,'pt':24}]}]}
        self.assertTrue(validate(p))
        fixed,changes,issues=repair(p)
        self.assertFalse(issues,issues)
        self.assertEqual({k:v for k,v in fixed['slides'][0]['elements'][1].items() if k!='color'},p['slides'][0]['elements'][1])
        self.assertTrue(changes)
    def test_targeted_rewrite_rejects_fact_loss(self):
        import engine
        from unittest.mock import patch
        p={'slides':[{'intent':'Economy','elements':[{'type':'text','text':'CAIT projected ₹30,000 crore in 2025 across India, not audited.','x':1,'y':1,'w':3,'h':.6,'pt':20}]}]}
        issue={'kind':'text_fit','slide':0,'element':0,'lines':2,'need':.8}
        with patch.object(engine,'chat',return_value=('{"text":"A big festival."}',{'cost':0})):
            with self.assertRaisesRegex(ValueError,'dropped protected fact'):
                engine.targeted_rewrite(p,issue,'mock','http://localhost','/tmp/no-write-mock')
    def test_targeted_patch(self):
        import engine
        p={'slides':[{'elements':[{'type':'text','text':'A','x':1,'y':1,'w':2,'h':1,'pt':24},{'type':'text','text':'B','x':5,'y':1,'w':2,'h':1,'pt':24}]}]}
        q=engine.apply_patches(p,[{'slide':1,'element':0,'changes':{'x':2}}])
        self.assertEqual(q['slides'][0]['elements'][0]['x'],2)
        self.assertEqual(q['slides'][0]['elements'][1],p['slides'][0]['elements'][1])
        self.assertEqual(p['slides'][0]['elements'][0]['x'],1)
        self.assertEqual(engine.apply_patches(p,[{'slide':1,'element':99,'changes':{'x':3}}]),p)
    def test_card_overflow_caught_before_export(self):
        p={'slides':[{'elements':[{'type':'box','x':.6,'y':1.5,'w':12,'h':5.5,'fill':'FFFFFF'},
             {'type':'text','text':'Source: CAIT projection','x':1,'y':6.9,'w':10,'h':.4,'pt':10}]}]}
        self.assertIn('card_overflow',{i['kind'] for i in validate(p)})
        fixed,_,issues=repair(p)
        self.assertTrue(issues)  # no valid vertical room: do not silently crop
    def test_source_row_reflows_without_dropping_url(self):
        p={'slides':[{'elements':[{'type':'text','text':'Sources','x':.5,'y':.5,'w':12,'h':.6,'pt':24},
           {'type':'text','text':'Source https://cait.in/a-long-url-with-projection','x':.5,'y':1.3,'w':12,'h':.4,'pt':12},
           {'type':'text','text':'CAIT 2024 estimate','x':.5,'y':1.8,'w':12,'h':.4,'pt':12}]}]}
        fixed,changes,issues=repair(p)
        self.assertFalse(issues)
        self.assertEqual(fixed['slides'][0]['elements'][1]['text'],p['slides'][0]['elements'][1]['text'])
        self.assertTrue(any(c['kind']=='downstream_text_reflow' for c in changes) or not validate(p))
    def test_unsupported_growth_claim(self):
        import engine
        p={'slides':[{'elements':[{'type':'text','text':'The economic impact continues to grow.'}]}]}
        self.assertEqual(engine.unsupported_claims(p)[0]['element'],0)
        p['slides'][0]['elements'][0]['text']='CAIT projected ₹30,000 crore business in 2025.'
        self.assertEqual(engine.unsupported_claims(p),[])
        import tempfile
        from pathlib import Path
        p['slides'][0]['elements'][0].update(text='Economic impact continues to grow',x=1,y=1,w=5,h=.8,pt=17)
        with tempfile.TemporaryDirectory() as d:
            engine.prepare.enforce_claims=False
            engine.prepare(p,Path(d),0)
            engine.prepare.enforce_claims=True
            try:
                with self.assertRaisesRegex(ValueError,'unsupported growth claim'):engine.prepare(p,Path(d),0)
            finally:engine.prepare.enforce_claims=False
    def test_pdf_render_audit_catches_actual_card_escape(self):
        import engine,json
        from pathlib import Path
        from unittest.mock import patch
        import fitz
        p={'slides':[{'elements':[{'type':'box','x':.6,'y':1.5,'w':12,'h':5.5},
            {'type':'text','text':'Source note','x':1,'y':6.85,'w':10,'h':.4,'pt':10}]}]}
        doc=fitz.open();page=doc.new_page(width=13.333*72,height=7.5*72)
        page.insert_text((1*72,7.05*72),'Source note',fontsize=10)
        with Path('/tmp/mock-overflow.pdf').open('wb') as f:f.write(doc.tobytes())
        issues=engine.audit_rendered_text(p,'/tmp/mock-overflow.pdf')
        self.assertIn('rendered_card_overflow',{i['kind'] for i in issues})
    def test_bounds_overlap(self):
        p={'slides':[{'elements':[{'type':'text','text':'A','x':12,'y':.1,'w':2,'h':1,'pt':24},{'type':'text','text':'B','x':1,'y':1,'w':3,'h':1,'pt':24},{'type':'text','text':'C','x':2,'y':1,'w':3,'h':1,'pt':24}]}]}
        kinds={x['kind'] for x in validate(p)}
        self.assertIn('bounds',kinds);self.assertIn('text_overlap',kinds)

if __name__=='__main__':unittest.main()

class ParsingTests(unittest.TestCase):
    def test_salvage_complete_json_after_preface(self):
        import engine
        self.assertEqual(engine.parse_json('```json\n{"slides": []}\n```'),{'slides':[]})
    def test_malformed_json_is_not_fabricated(self):
        import engine
        with self.assertRaises(ValueError):engine.parse_json('{"slides": [,,,], "palette": {}}')
    def test_truncated_plan_rejected_without_render(self):
        import engine,io,json,tempfile
        from unittest.mock import patch
        from pathlib import Path
        class APIResponse:
            def __init__(self,body):self.body=io.BytesIO(json.dumps(body).encode())
            def read(self,*args):return self.body.read(*args)
            def __enter__(self):return self
            def __exit__(self,*args):pass
        answer={'choices':[{'finish_reason':'length','message':{'content':'{"palette":{},"slides":['}}],
                'usage':{'cost':0,'completion_tokens':5600}}
        with tempfile.TemporaryDirectory() as tmp,patch.object(engine.urllib.request,'urlopen',return_value=APIResponse(answer)):
            import os
            with patch.dict(os.environ,{'OPENROUTER_API_KEY':'mock'}):
                with self.assertRaisesRegex(ValueError,'truncated at token cap'):
                    engine.chat([], 'mock', raw_path=Path(tmp)/'raw.json')
            self.assertEqual(json.loads((Path(tmp)/'raw.json').read_text())['usage']['completion_tokens'],5600)
    def test_actual_malformed_gemini_payload_salvage(self):
        import engine,json
        from pathlib import Path
        # Captured after a paid response finished normally but was not valid JSON.
        # Fixture omits original prose and URLs while retaining exact broken shape.
        fixture=Path(__file__).parent/'fixtures'/'malformed-gemini-plan.json.txt'
        raw=fixture.read_text()
        with self.assertRaises(json.JSONDecodeError):json.loads(raw)
        plan=engine.normalize_plan_schema(engine.parse_json(raw))
        self.assertEqual(len(plan['slides']),2)
        self.assertEqual(plan['slides'][0]['background'],'cream')
        self.assertEqual(plan['slides'][0]['elements'][1]['type'],'text')
        self.assertEqual(plan['slides'][1]['elements'][0]['text'],'Source: example.org')
    def test_no_unbounded_json_repair(self):
        import engine,json
        with self.assertRaises(json.JSONDecodeError):engine.parse_json('{"slides": [,,,], "palette": {}}')
    def test_actual_payload_file_salvages_when_available(self):
        import engine,json
        from pathlib import Path
        path=Path('/tmp/arrakis-design-paid-onerun/raw-planner.json')
        if not path.exists():self.skipTest('live payload not retained in scratch')
        raw=json.loads(path.read_text())['message']['content']
        plan=engine.normalize_plan_schema(engine.parse_json(raw))
        self.assertEqual(len(plan['slides']),6)
        self.assertEqual(len(plan['slides'][0]['elements']),5)
        self.assertEqual(plan['slides'][0]['elements'][0]['type'],'image')
    def test_unknown_nested_schema_rejected(self):
        import engine
        with self.assertRaisesRegex(ValueError,'unknown element schema'):
            engine.normalize_plan_schema({'palette':{},'slides':[{'background':'cream','elements':[{'title':{'text':'oops'}}]}]})
    def test_prompt_is_compact_but_source_complete(self):
        import engine
        brief='Explain the festival economy without audited figures.'
        sources='CAIT ₹30,000 crore estimate. https://cait.in/source'
        result=engine.prompt(brief,[{'id':'a','file':'secret/local/path','description':'idol'}],sources)
        self.assertIn(brief,result);self.assertIn(sources,result)
        self.assertIn('under 4200 output tokens',result)
        self.assertNotIn('secret/local/path',result)
    def test_refuse_truncated_json(self):
        import engine
        with self.assertRaises(ValueError):engine.parse_json('{"slides": [')
