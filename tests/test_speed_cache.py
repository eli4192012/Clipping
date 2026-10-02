import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from upgrades import transcript_file,signature
from jobs import get_transcript,analyze
from topic_cache import reviewed_topics

class SpeedCacheTests(unittest.TestCase):
 def test_visual_settings_share_speech(self):
  with tempfile.TemporaryDirectory() as tmp:
   settings={'quality':'Higher quality','alignment':True,'speakers':False}
   self.assertEqual(transcript_file(tmp,dict(settings,scenes=True)),transcript_file(tmp,dict(settings,scenes=False)))
   legacy=Path(tmp)/('transcript-'+signature(dict(settings,scenes=True))+'.json');legacy.write_text('{}')
   self.assertEqual(transcript_file(tmp,settings),legacy)
 def test_alignment_reuses_raw_transcription(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=dict(folder=tmp,source=str(Path(tmp)/'unused.mp4'))
   transcript={'language':'en','words':[],'sentences':[]}
   (Path(tmp)/'transcript.json').write_text(json.dumps(transcript))
   with patch('jobs.transcribe',side_effect=AssertionError('Retranscribed')),patch('jobs.worker',return_value=transcript) as worker:
    get_transcript(p,dict(quality='Balanced',alignment=True),lambda *a:None)
    self.assertEqual(worker.call_args.args[0],'speech_details')
 def test_podcast_saved_proposals_skip_loading_all_models(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=dict(cache_dir=tmp,mode='Podcast',quality='Balanced',sentences=[],minimum=5,maximum=30)
   c=dict(start=0,end=6,text='A complete useful point.',rank=1,passed=True)
   loader=Mock(return_value=(None,None,None,None))
   with patch('topic_cache.topic_candidates',return_value=[c]),patch('topic_cache.exact_cut_review',return_value=c):
    first=reviewed_topics(p,loader)
   loader.assert_called_once()
   with patch('topic_cache.topic_candidates',side_effect=AssertionError('Repeated proposals')):
    second=reviewed_topics(p,Mock(side_effect=AssertionError('Loaded model on cache hit')))
   self.assertEqual(first,second)
 def test_proposal_cache_includes_transcript_and_quality(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=dict(cache_dir=tmp,mode='Podcast',quality='Balanced',sentences=[],minimum=5,maximum=30)
   c=dict(start=0,end=6,text='Point.',rank=1,passed=True)
   with patch('topic_cache.topic_candidates',return_value=[c]) as propose,patch('topic_cache.exact_cut_review',return_value=c):
    for options in (p,dict(p,quality='Higher quality'),dict(p,sentences=[{'text':'changed'}])):
     reviewed_topics(options,lambda:(None,None,None,None))
    self.assertEqual(propose.call_count,3)
 def test_coverage_changes_do_not_repeat_review(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source';source.write_text('test')
   p=dict(folder=tmp,source=str(source),duration=60)
   s=dict(mode='Podcast',quality='Balanced',minimum=5,maximum=30,vision=False,semantic=True,windows=6,coverage=1.)
   c=dict(start=0,end=10,text='A self contained topic.',rank=1,passed=True,topic_group=True,title='Topic')
   with patch('jobs.get_transcript',return_value={'words':[],'sentences':[]}),patch('jobs.worker',return_value=[c]) as worker:
    a=analyze(p,s,lambda *a:None);b=analyze(p,dict(s,coverage=.5),lambda *a:None)
    self.assertEqual(worker.call_count,1);self.assertNotEqual(a,b)
    self.assertEqual(json.loads(Path(a).read_text()),json.loads(Path(b).read_text()))

class ProposalWindowTests(unittest.TestCase):
 def test_no_redundant_final_window_and_full_coverage(self):
  from topics import topic_candidates
  class Tokenizer:
   def __init__(self):self.ids=[]
   def apply_chat_template(self,messages,**kwargs):
    data=json.loads(messages[0]['content'].rsplit('\n',1)[-1])
    self.ids.extend(s['id'] for s in data)
    return ''
  for count,expected in [(1,1),(60,1),(72,1),(73,2),(100,2),(120,2),(121,3)]:
   tokenizer=Tokenizer();generate=Mock(return_value='{"topics":[]}')
   sentences=[dict(start=i,end=i+1,text='Sentence.') for i in range(count)]
   topic_candidates(sentences,5,30,'Podcast',None,tokenizer,generate,None)
   self.assertEqual(generate.call_count,expected)
   self.assertEqual(set(tokenizer.ids),set(range(count)))

class DetectReuseTests(unittest.TestCase):
 def test_three_samples_share_one_speech_model(self):
  from video_type import detect
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source';source.write_bytes(b'fixture')
   p=dict(folder=tmp,source=str(source),duration=180.,title='Example')
   container=Mock();container.__enter__=Mock(return_value=SimpleNamespace(streams=SimpleNamespace(audio=[1])));container.__exit__=Mock(return_value=False)
   model=object()
   with patch('av.open',return_value=container),patch('video_type.subprocess.run',return_value=SimpleNamespace(returncode=0)),patch('engine.speech_model',return_value=model) as load,patch('engine.transcribe',return_value={'sentences':[]}) as transcribe,patch('framing.inspect_framing',return_value={}):
    detect(p)
    load.assert_called_once();self.assertEqual(transcribe.call_count,3)
    self.assertTrue(all(call.kwargs['model'] is model for call in transcribe.call_args_list))
