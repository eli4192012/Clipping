"""Isolated local visual classification; stdout is JSON only."""
from resource_limits import configure
configure()
from resource_limits import configure_mlx
configure_mlx()
import contextlib
import json
import sys
from pathlib import Path

if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text())
    import fcntl
    lock=(Path(__file__).parent/'work/model.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX)
    with contextlib.redirect_stdout(sys.stderr):
        from mlx_vlm import load, generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config
        from vision_sports import VISION
        from PIL import Image
        import mlx.core as mx
        mx.set_cache_limit(64 * 1024 * 1024)
        model_path=request.get('model_path',str(VISION))
        model,processor=load(model_path); config=load_config(model_path)
        sheet=Image.open(request['sheet'])
        prompt='''Describe this image in one short sentence, focusing on camera framing and players' positions. Is it a close-up of a player or people, a wide view of both teams lined up before the snap, or a wide view of a play in progress? Do not read or infer events from the scoreboard.'''
        formatted=apply_chat_template(processor,config,prompt,num_images=1)
        labels=[]
        descriptions=[]
        from engine import parse_json
        for i in range(request.get('frame_count',16)):
            x,y=i%4*280,i//4*180
            frame=sheet.crop((x,y,x+280,y+156))
            result=generate(model,processor,formatted,image=[frame],max_tokens=70,temperature=0,verbose=False)
            text=(result.text if hasattr(result,'text') else str(result)).strip()
            description=text
            from sports_discovery import classify_frame
            label=classify_frame(text)
            descriptions.append(description)
            labels.append(label)
            print(f'Frame {i}: {label}',file=sys.stderr,flush=True)
            mx.clear_cache()
    print(json.dumps({'labels':labels,'descriptions':descriptions,'reason':'Each sampled frame was classified locally as wide setup, wide action, closeup, or other.'}))
