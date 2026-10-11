"""Conservative process-wide limits for a usable desktop during local processing."""
import os,threading
from contextvars import ContextVar
HEAVY_JOB_LOCK=threading.Lock()
HEAVY_JOB_FD=ContextVar('clipping_heavy_job_fd',default=None)


def inherited_lock_fds():
    """Queue children keep the existing heavy-job lock through parent loss."""
    value=HEAVY_JOB_FD.get()
    if value is None:value=os.environ.get('CLIPPING_HEAVY_LOCK_FD')
    if value is None:return ()
    try:
        fd=int(value);os.fstat(fd)
    except (ValueError,OSError):return ()
    return (fd,)

def configure():
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[key]='2'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    try:
        if os.getpriority(os.PRIO_PROCESS,0)<10:os.setpriority(os.PRIO_PROCESS,0,10)
    except (AttributeError,OSError):pass

def configure_mlx():
    configure()
    import mlx.core as mx
    # Fail with a recoverable allocation error rather than consume the entire Mac.
    mx.set_cache_limit(128*1024*1024)
    mx.set_memory_limit(3*1024**3)
