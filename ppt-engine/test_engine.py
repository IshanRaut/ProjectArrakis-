"""Local mock smoke test of planner -> renderer -> PDF -> visual critic protocol, no paid API."""
import json,threading,tempfile,os
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import engine
calls=[]
plan={'rationale':'Mock design decision for test only','palette':{'cream':'F8F2E8','ink':'291628'},'slides':[{'background':'cream','intent':'Test editable native deck','elements':[{'type':'text','text':'Mock plan approved','x':.6,'y':.6,'w':10,'h':1,'pt':36,'color':'ink','bold':False,'align':'left'},{'type':'image','asset':'idol_stage','x':7,'y':2,'w':5,'h':4,'focus':[.5,.5]}]}]}
class H(BaseHTTPRequestHandler):
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(body)
  response=plan if len(calls)==1 else {'approved':True,'issues':[]}
  b=json.dumps({'choices':[{'message':{'content':json.dumps(response)}}],'usage':{'prompt_tokens':42,'completion_tokens':24}}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
server=HTTPServer(('127.0.0.1',0),H);th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
os.environ['OPENROUTER_API_KEY']='mock-only-not-real'
with tempfile.TemporaryDirectory() as folder:
 root=Path(__file__).parent
 class A: pass
 a=A();a.brief=str(root/'brief.txt');a.assets=str(root/'assets.json');a.sources=str(root/'sources.txt');a.output=folder+'/out';a.model='mock';a.vision_model='mock';a.api_url=f'http://127.0.0.1:{server.server_port}/chat/completions';a.max_revisions=2
 assert engine.run(a)==0
 assert len(calls)==2
 assert len(calls[1]['messages'][1]['content'])==2
 from pptx import Presentation
 assert len(Presentation(a.output+'/deck.pptx').slides)==1
 assert Path(a.output+'/deck.pdf').is_file()
 assert json.loads(Path(a.output+'/run-log.json').read_text())['iterations'][1]['stage']=='critic'
 assert json.loads(Path(a.output+'/render-audit-0.json').read_text())==[]
 print('PASS local mock: planner, editable PPTX, PDF render, image-bearing critic call, approval, log')
server.shutdown()
