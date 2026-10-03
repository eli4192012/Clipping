"""Persistent project library and per-analysis settings snapshots."""
import json,re,uuid,itertools
from pathlib import Path


def read(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default


def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(data,indent=2));temp.replace(path)


def save_run(project,settings,result):
    folder=Path(project['folder']);result=Path(result).resolve()
    write(folder/'project.json',project)
    runs=read(folder/'project-runs.json',{})
    runs[result.name]=dict(result=str(result),settings=dict(settings),saved_at=result.stat().st_mtime)
    write(folder/'project-runs.json',runs)


def runs_for(project):
    folder=Path(project['folder']);saved=read(folder/'project-runs.json',{})
    current=read(folder/'ui-settings.json',{})
    from upgrades import signature
    results=[]
    for path in folder.glob('clips-*.json'):
        clips=read(path,None)
        if not isinstance(clips,list) or any(not isinstance(c,dict) or not {'start','end','text'}<=c.keys() for c in clips):continue
        match=re.match(r'clips-v\d+-(Interview|Podcast|Sports)-(\d+)-(\d+)-(\d+|all)-(vision\d+|ai|basic)',path.name)
        legacy=re.match(r'clips-(\d+)-(\d+)-(ai|basic)\.json$',path.name)
        if not match and not legacy:continue
        row=saved.get(path.name)
        if not row:
            mode,minimum,maximum,count,variant=match.groups() if match else ('Interview',legacy[1],legacy[2],'all',legacy[3])
            settings=dict(current,quality='Balanced',alignment=False,speakers=False,scenes=False,mode=mode,minimum=int(minimum),maximum=int(maximum),semantic=variant=='ai',vision=variant.startswith('vision'),windows=int(variant[6:]) if variant.startswith('vision') else 6)
            # Today's editor selection must not relabel an unregistered older run.
            settings.pop('editor_model',None)
            from local_editor import CHOICES,cache_tag
            for editor in CHOICES:
                tag=cache_tag(dict(settings,editor_model=editor))
                if tag and tag in path.name:settings['editor_model']=editor;break
            settings['shorts_editor']='-shorts1-' in path.name
            # Recover old run model settings from their recorded signature, not today's UI choice.
            for quality,scenes,speakers,alignment in itertools.product(['Balanced','Higher quality'],[False,True],[False,True],[False,True]):
                trial=dict(settings,quality=quality,scenes=scenes,speakers=speakers,alignment=alignment)
                if signature(trial) in path.name:settings=trial;break
            settings.setdefault('quality','Balanced');settings.setdefault('portrait',False)
            row=dict(result=str(path.resolve()),settings=settings,saved_at=path.stat().st_mtime)
        results.append(dict(row,count=len(clips)))
    return sorted(results,key=lambda r:r['saved_at'],reverse=True)


def library(root):
    projects=[]
    for folder in Path(root).iterdir():
        if not folder.is_dir():continue
        p=read(folder/'project.json',None)
        if not isinstance(p,dict):
            meta=read(folder/'import.json',{})
            if not meta.get('filename'):continue
            p=dict(source=str(folder/meta['filename']),folder=str(folder),title=meta.get('title',folder.name))
        if not all(k in p for k in ['source','title']):continue
        p=dict(p,folder=str(folder))
        runs=runs_for(p)
        projects.append(dict(project=p,runs=runs,updated=max([r['saved_at'] for r in runs]+[(folder/'project.json' if (folder/'project.json').is_file() else folder/'import.json').stat().st_mtime]),available=Path(p['source']).is_file()))
    return sorted(projects,key=lambda p:p['updated'],reverse=True)
