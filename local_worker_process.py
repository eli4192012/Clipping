"""Poll atomic worker status without blocking or filling subprocess pipes."""
import json,subprocess,time
import math
from app_logging import log_exception, log_worker_failure, redact
from ffmpeg_export import stop_process

LOCAL_WORKER_API = 3


def run_local(command,request,result,env,timeout,progress=None,progress_timeout=False):
    from resource_limits import inherited_lock_fds
    inherited=inherited_lock_fds()
    if inherited:env=dict(env,CLIPPING_HEAVY_LOCK_FD=str(inherited[0]))
    status=request.with_name('progress.json')
    data=json.loads(request.read_text());data['progress']=str(status);request.write_text(json.dumps(data))
    # Enforce the topic policy here too: older callers may omit the new flag.
    progress_timeout=progress_timeout or data.get('task')=='topics'
    with request.with_name('stdout.log').open('w+') as out,request.with_name('stderr.log').open('w+') as err:
        process=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True,pass_fds=inherited)
        begun=time.monotonic();last_activity=begun;last=None
        try:
            while True:
                if (progress or progress_timeout) and status.exists():
                    event=None
                    try:
                        event=json.loads(status.read_text())
                        fraction=float(event['fraction'])
                        if not math.isfinite(fraction) or not 0<=fraction<=1 or not isinstance(event['label'],str):raise ValueError('Invalid progress')
                        event=dict(fraction=fraction,label=event['label'])
                    except (OSError,ValueError,TypeError,KeyError):event=None
                    if event is not None and event!=last:
                        if progress:progress(event['fraction'],event['label'])
                        last=event;last_activity=time.monotonic()
                code=process.poll()
                if code is not None:break
                now=time.monotonic()
                if now-(last_activity if progress_timeout else begun)>timeout or (progress_timeout and now-begun>86400):
                    cause=('The 24-hour safety limit was reached.' if progress_timeout and now-begun>86400 else
                           'No new review progress was reported within the time limit.' if progress_timeout else
                           'This worker exceeded its processing time limit.')
                    raise TimeoutError('Local analysis reached its time limit. '+cause+' Completed reviews are saved; resume with the same settings to reuse them.')
                time.sleep(.25)
        except BaseException:
            log_exception('Local worker stopped')
            raise
        finally:
            if process.poll() is None:stop_process(process)
        if code or not result.exists():
            err.seek(0,2);err.seek(max(0,err.tell()-12000))
            details=err.read()
            log_worker_failure(details)
            raise RuntimeError('Local worker failed: '+redact(details[-1400:]))
        return json.loads(result.read_text())
