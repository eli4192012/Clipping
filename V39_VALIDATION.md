# v3.9 validation

75 existing automated tests pass; changed modules compile. Resource limits are installed before model imports. Live process inspection was denied by this session's sandbox, and MLX cannot access Metal here, so actual CPU/GPU/memory pressure and responsiveness have not been verified. Do not interpret the limits as a measured speedup or guaranteed prevention of lag.

A full server restart is required. Restart was not attempted from this restricted session because it cannot validate the GPU-enabled runtime.
