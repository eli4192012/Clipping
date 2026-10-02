# v5.15 validation

152 tests passed, including subprocess progress delivery, large output without pipe blockage, worker termination on timeout, invalid interview context avoiding model loading, and proposal-window cache reuse.

The reported 34-minute Higher quality podcast completed in 3169.7 seconds (52m 50s), producing 71 reviewed candidates and 41 selected clips. The UI previously reported no topic-stage progress while those candidates were reviewed sequentially.

Two existing candidates were reviewed again using the same local 4B model with concise response instructions. Both produced parsed decisions; measured review times were 14.41 seconds (269-word candidate) and 12.76 seconds (25-word candidate), excluding model load. Original sequential saved-review intervals were approximately 37 and 24 seconds. This is a two-sample timing check, not a controlled whole-video speed guarantee or full editorial quality benchmark.

No whole-video re-analysis was performed. Completed results, source, transcript and saved reviews were preserved; reopening the completed project reuses them.
