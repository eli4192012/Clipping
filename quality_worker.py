"""One model process at a time: releases model memory when each task ends."""
from resource_limits import configure
configure()
import json
import sys
from pathlib import Path
from upgrades import TURBO,SPEAKERS,sentences_from_words,assign_speakers

def run(task,p,progress=lambda p,label:None):
    if task!='speech_details':
        from resource_limits import configure_mlx
        configure_mlx()
    if task=='transcription':
        import mlx_whisper
        import imageio_ffmpeg,os
        # mlx-whisper audio loading needs the ffmpeg executable on PATH.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'ffmpeg').symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
            os.environ['PATH']=tmp+os.pathsep+os.environ.get('PATH','')
            result=mlx_whisper.transcribe(p['source'],path_or_hf_repo=str(TURBO),word_timestamps=True,condition_on_previous_text=False,verbose=False)
        words=[dict(start=float(w['start']),end=float(w['end']),text=w['word'].strip()) for s in result['segments'] for w in s.get('words',[]) if w['word'].strip()]
        return dict(language=result['language'],words=words,sentences=sentences_from_words(words),backend='Whisper large-v3-turbo / MLX')
    if task=='publishing':
        from local_editor import load_bundle
        from engine import parse_json
        model,tokenizer,generate,sampler=load_bundle(p)
        prompt='Write posting copy for this transcript DATA. Return JSON title (specific short headline), description (1–2 sentences). Title must be at most 100 characters including spaces. Do not generate hashtags. Preserve uncertainty, no invented results or unsupported hype. Only describe what the clip says. Transcript: '+json.dumps(p['text'])
        formatted=tokenizer.apply_chat_template([dict(role='user',content=prompt)],tokenize=False,add_generation_prompt=True,enable_thinking=False)
        return parse_json(generate(model,tokenizer,prompt=formatted,max_tokens=300,sampler=sampler,verbose=False))
    if task=='opening_hook':
        from local_editor import load_bundle
        from opening_hooks import generate_local
        return generate_local(p['text'],p.get('opening_speech',''),p.get('style_lessons',[]),load_bundle(p,large=True),progress)
    if task=='ending_review':
        from local_editor import load_bundle
        from ending_review import generate_local
        return generate_local(p['data'],load_bundle(p,large=True),progress)
    if task=='social_copy':
        from local_editor import load_bundle
        from social_copy import generate_local
        if not p.get('text','').strip():raise ValueError('This clip needs a speech transcript for AI posting text.')
        return generate_local(p['text'],load_bundle(p,large=True),progress)
    if task=='headline':
        from local_editor import load_bundle
        from polish import title_for
        model,tokenizer,generate,sampler=load_bundle(p)
        return {'title':title_for(p['text'],model,tokenizer,generate,sampler)}
    if task=='topics':
        from topic_cache import reviewed_topics
        def load_bundle():
            from local_editor import load_bundle as load_editor
            return load_editor(p,large=bool(p.get('shorts_editor')))
        return reviewed_topics(p,load_bundle,progress)
    if task=='shorts_edit':
        from shorts_editor import edit_candidate
        from local_editor import selected_editor,IDENTITIES
        def load_bundle():
            from local_editor import load_bundle as load_editor
            return load_editor(p,large=True)
        return edit_candidate(p['candidate'],p['sentences'],p['words'],p['maximum'],p['quality'],p['cache_dir'],
            load_bundle,p.get('variant','Balanced'),p.get('baseline'),progress,
            editor_identity=IDENTITIES[selected_editor(p,large=True)] if p.get('editor_model') else None)
    if task=='review':
        import engine
        from local_editor import load_bundle
        return engine.review_candidates(p['sentences'],p['candidates'],mode=p['mode'],categories=p.get('categories',[]),
            bundle=load_bundle(p))
    if task=='speech_details':
        import numpy as np
        import subprocess,imageio_ffmpeg
        raw=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',p['source'],'-f','f32le','-ac','1','-ar','16000','-'])
        audio=np.frombuffer(raw,dtype=np.float32).copy();transcript=p['transcript']
        if p.get('alignment'):
            if transcript['language']!='en':raise RuntimeError('Precise alignment is installed for English only. Turn it off for this language.')
            import whisperx
            model,meta=whisperx.load_align_model(language_code=transcript['language'],device='cpu',model_dir=str(Path(__file__).parent/'models/alignment'))
            aligned=whisperx.align(transcript['sentences'],model,meta,audio,'cpu',return_char_alignments=False)
            words=[dict(start=w['start'],end=w['end'],text=w['word']) for w in aligned['word_segments'] if 'start' in w and 'end' in w]
            if not words or len(words)!=len(aligned['word_segments']):raise RuntimeError('Some words could not be aligned. Turn off precise alignment to retain every word.')
            transcript['words']=words
            del model
        if p.get('speakers'):
            import torch
            from pyannote.audio import Pipeline
            pipeline=Pipeline.from_pretrained(str(SPEAKERS))
            result=pipeline({'waveform':torch.from_numpy(audio).unsqueeze(0),'sample_rate':16000})
            turns=[dict(start=turn.start,end=turn.end,speaker=speaker) for turn,speaker in result.exclusive_speaker_diarization]
            transcript['speaker_turns']=turns
            assign_speakers(transcript['words'],turns)
        transcript['sentences']=sentences_from_words(transcript['words'])
        return transcript
    raise ValueError('Unknown local worker task')

if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text())
    import fcntl
    with (Path(__file__).parent/'work/model.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        from project_store import write
        def progress(fraction,label):
            if request.get('progress'):write(Path(request['progress']),dict(fraction=fraction,label=label))
        progress(0,'Loading the selected local model when needed')
        output=run(request['task'],request['payload'],progress)
    Path(request['result']).write_text(json.dumps(output))
