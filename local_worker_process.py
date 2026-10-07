"""Poll atomic worker status without blocking or filling subprocess pipes."""
import json,subprocess,time
from app_logging import log_exception, log_worker_failure, redact
from ffmpeg_export import stop_process

def run_local(command,request,result,env,timeout,progress=None):
    status=request.with_name('progress.json')
    data=json.loads(request.read_text());data['progress']=str(status);request.write_text(json.dumps(data))
    with request.with_name('stdout.log').open('w+') as out,request.with_name('stderr.log').open('w+') as err:
        process=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
        begun=time.monotonic();last=None
        try:
            while True:
                if progress and status.exists():
                    try:
                        event=json.loads(status.read_text())
                        if event!=last:progress(event['fraction'],event['label']);last=event
                    except (OSError,ValueError,KeyError):pass
                code=process.poll()
                if code is not None:break
                if time.monotonic()-begun>timeout:
                    raise TimeoutError('Local analysis reached its time limit. Completed reviews are saved; retry to resume them.')
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
