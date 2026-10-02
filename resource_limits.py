"""Conservative process-wide limits for a usable desktop during local processing."""
import os,threading
HEAVY_JOB_LOCK=threading.Lock()

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
