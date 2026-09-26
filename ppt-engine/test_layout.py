import unittest
from layout import measure,validate,repair

class LayoutTests(unittest.TestCase):
    def test_measure_multiline_and_markup(self):
        a,_=measure('short',32,4)
        b,n=measure('<b>Long source label</b> ' * 8,32,4)
        self.assertGreater(b,a);self.assertGreater(n,1)
    def test_targeted_repair(self):
        p={'slides':[{'elements':[{'type':'text','text':'A long headline that cannot fit in a tiny box','x':1,'y':1,'w':4,'h':.35,'pt':40},{'type':'text','text':'Second','x':1,'y':4,'w':3,'h':.8,'pt':24}]}]}
        self.assertTrue(validate(p))
        fixed,changes,issues=repair(p)
        self.assertFalse(issues,issues)
        self.assertEqual(fixed['slides'][0]['elements'][1],p['slides'][0]['elements'][1])
        self.assertTrue(changes)
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
