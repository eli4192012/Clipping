import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from content_categories import *
class Categories(unittest.TestCase):
 def test_limit_and_auto(self):
  for values in [[],['Interview','Podcast','Travel'],[AUTO,'Interview'],['invalid']]:
   with self.assertRaises(ValueError):validate(values)
  self.assertEqual(validate(['Interview','Travel']),['Interview','Travel'])
 def test_routes(self):
  self.assertEqual(route(['American football']),'Sports')
  self.assertEqual(route(['Sports','American football']),'Sports')
  self.assertEqual(route(['American football','Interview']),'Interview')
  for name in ('Basketball','Soccer','Music','Gaming'):self.assertEqual(route([name]),'Podcast')
 def test_all_guidance(self):
  self.assertEqual(len(GUIDANCE),28)
  self.assertEqual(len(set(GUIDANCE.values())),28)
  self.assertIn('dish',guidance(['Food & Cooking']))
  self.assertIn('attribution',guidance(['News']))
 def test_cache_order_and_transcript_reuse(self):
  from upgrades import transcript_file
  self.assertEqual(cache_tag({'categories':['Interview','Travel']}),cache_tag({'categories':['Travel','Interview']}))
  self.assertNotEqual(cache_tag({'categories':['Food & Cooking']}),cache_tag({'categories':['News']}))
  self.assertEqual(transcript_file(Path('/tmp'),{'categories':['News']}),transcript_file(Path('/tmp'),{'categories':['Travel']}))
 def test_callback(self):
  import streamlit as st
  state={'picker':[AUTO,'Travel'],'picker-accepted':[AUTO]}
  with patch.object(st,'session_state',state),patch.object(st,'toast'):
   update_selection('picker');self.assertEqual(state['picker'],['Travel'])
   state['picker']=['Travel','Interview'];update_selection('picker')
   state['picker']=['Travel','Interview','News'];update_selection('picker')
   self.assertEqual(state['picker'],['Travel','Interview'])
   state['picker']=['Travel','Interview',AUTO];update_selection('picker');self.assertEqual(state['picker'],[AUTO])
 def test_prompt_wiring(self):
  from topics import topic_candidates,exact_cut_review
  class Tokenizer:
   def apply_chat_template(self,messages,**kwargs):return messages[0]['content']
  prompts=[]
  def generate(*args,**kwargs):
   prompts.append(kwargs['prompt']);return '{"topics":[],"standalone":true,"complete_ending":true,"faithful":true}'
  topic_candidates([dict(start=0,end=8,text='This recipe makes soup.')],5,60,'Podcast',None,Tokenizer(),generate,None,categories=['Food & Cooking'])
  exact_cut_review(dict(start=0,end=8,text='This recipe makes soup.'),None,Tokenizer(),generate,None,categories=['Food & Cooking'])
  self.assertTrue(all('necessary ingredients' in p for p in prompts));self.assertEqual(len(prompts),2)
