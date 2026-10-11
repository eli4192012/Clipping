"""Bounded-memory YAMNet inference. No network access or transcript work."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
os.environ.setdefault('CUDA_VISIBLE_DEVICES','-1')
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','1')


def load():
    sys.path.insert(0,str(ROOT/'vendor/yamnet'))
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')
    import yamnet,params
    model=yamnet.yamnet_frames_model(params.Params())
    model.load_weights(str(ROOT/'models/sound-yamnet/yamnet.h5'))
    return model,yamnet.class_names(str(ROOT/'vendor/yamnet/yamnet_class_map.csv'))


def run(request,progress=lambda p,label:None):
    import numpy as np
    model,labels=load();frames=[];levels=[];offset=0.;sample_rate=16000;chunk_seconds=30
    command=[request['ffmpeg'],'-v','error','-i',request['source'],'-map','0:a:0','-vn','-ac','1','-ar',str(sample_rate),
             '-af','aresample=async=1:first_pts=0','-f','f32le','-']
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        while True:
            raw=process.stdout.read(sample_rate*chunk_seconds*4)
            if not raw:break
            audio=np.frombuffer(raw,dtype='<f4').copy();length=len(audio)/sample_rate
            predictions=model(audio)[0].numpy()
            for i,scores in enumerate(predictions):
                start=offset+i*.48;end=start+.96
                if end>offset+length+.001:continue  # ignore model padding
                indices=np.argsort(scores)[-6:][::-1]
                frames.append(dict(start=round(start,3),end=round(end,3),tags=[dict(label=str(labels[j]),score=round(float(scores[j]),4)) for j in indices]))
            for i in range(0,len(audio),sample_rate):
                segment=audio[i:i+sample_rate];rms=float(np.sqrt(np.mean(segment**2)))
                levels.append(dict(start=round(offset+i/sample_rate,3),end=round(offset+(i+len(segment))/sample_rate,3),
                    rms_db=round(20*float(np.log10(max(1e-8,rms))),2),peak=round(float(np.max(np.abs(segment))),4)))
            offset+=length
            progress(min(.99,offset/max(1,request['duration'])),f'Analyzing sound · {offset:.0f} of {request["duration"]:.0f} seconds read')
        if process.wait()!=0:raise RuntimeError('Could not decode the sound track.')
    finally:
        process.stdout.close()
        if process.poll() is None:process.terminate();process.wait()
    return dict(status='Local model estimates',frames=frames,levels=levels,decoded_seconds=offset)


if __name__=='__main__':
    from resource_limits import configure
    configure()
    import fcntl
    with (ROOT/'work/model.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if sys.argv[1]=='--check':
            import numpy as np
            model,_=load();assert model(np.zeros(16000,dtype=np.float32))[0].shape[1]==521
            print('Local YAMNet inference passed.')
        else:
            request=json.loads(Path(sys.argv[1]).read_text())
            from project_store import write
            def progress(p,label):
                if request.get('progress'):write(Path(request['progress']),dict(fraction=p,label=label))
            progress(0,'Loading the local sound model')
            write(Path(request['result']),run(request,progress))
