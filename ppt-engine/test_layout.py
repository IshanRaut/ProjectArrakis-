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
    def test_bounds_overlap(self):
        p={'slides':[{'elements':[{'type':'text','text':'A','x':12,'y':.1,'w':2,'h':1,'pt':24},{'type':'text','text':'B','x':1,'y':1,'w':3,'h':1,'pt':24},{'type':'text','text':'C','x':2,'y':1,'w':3,'h':1,'pt':24}]}]}
        kinds={x['kind'] for x in validate(p)}
        self.assertIn('bounds',kinds);self.assertIn('text_overlap',kinds)

if __name__=='__main__':unittest.main()

class ParsingTests(unittest.TestCase):
    def test_salvage_complete_json_after_preface(self):
        import engine
        self.assertEqual(engine.parse_json('Reasoning: done. {"slides": []} trailing'),{'slides':[]})
    def test_refuse_truncated_json(self):
        import engine
        with self.assertRaises(ValueError):engine.parse_json('{"slides": [')
