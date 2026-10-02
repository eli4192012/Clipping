# TransNet V2 benchmark · v5.7

Six preserved user-supplied problem exports were tested sequentially on this Mac. No new large runtime was installed: the benchmark reused existing PyTorch, ran on CPU with two threads at reduced priority, and loaded one approximately 30 MB converted checkpoint. It does not run in the app.

| Clip | Duration | PySceneDetect time | TransNet time | PySceneDetect transitions | TransNet transitions |
|---|---:|---:|---:|---:|---:|
| clip-72.5-122.5-d0d633.mp4 | 49.9s | 2.07s | 15.49s | 5 | 6 |
| clip-188.9-214.9-e47613.mp4 | 26.0s | 1.06s | 8.92s | 3 | 6 |
| clip-152.1-178.9-8f9558.mp4 | 26.8s | 0.99s | 9.08s | 4 | 4 |
| clip-97.3-109.3-97ae67.mp4 | 12.0s | 0.51s | 4.54s | 2 | 2 |
| clip-80.8-105.4-e6cfa3.mp4 | 24.6s | 0.60s | 6.72s | 0 | 0 |
| clip-45.5-53.8-609be6.mp4 | 8.3s | 0.22s | 2.24s | 0 | 0 |

Total detection time: PySceneDetect 5.45s; TransNet 46.98s (8.6× slower). Model initialization took 0.05s and is excluded from that total. Peak process RSS was 957 MiB; this is the combined benchmark process, not an isolated model-memory measurement.

## Findings

- TransNet found 18 transitions versus 14 for the existing AdaptiveDetector configuration. All 14 baseline detections have a TransNet detection within 0.15 seconds. Both found no transitions in the two interview examples.
- Inspected before/after frames around the four extra detections: 11.011s in clip-72.5 and 1.001s, 10.711s, 17.517s in clip-188.9. These show actual shot changes/dissolves, including replay transitions.
- This is useful shot-boundary evidence, not proof that TransNet understands a complete football play. A replay transition cannot establish the start or outcome of an event.
- Recommendation: keep the current default for speed; investigate TransNet only as an optional focused check around uncertain sports boundaries. It is not enabled in the app by this release.

## Reproducibility and limits

- Official model code: https://github.com/soCzech/TransNetV2/tree/master/inference-pytorch (MIT license preserved under work/transnet-benchmark/vendor).
- Third-party converted checkpoint: https://huggingface.co/MiaoshouAI/transnetv2-pytorch-weights . Loaded using torch.load(weights_only=True); parity against original TensorFlow weights was not independently established.
- Checkpoint SHA-256: 46520d66d4bf60414a4d82e0e94a92442ff950e34517a3718b2e54815e642b53
- Used native decoded frame order at 48×27 RGB, 100-frame windows, center 50 predictions, edge replication, sigmoid threshold 0.5, and peak of each consecutive positive interval.
- Baseline: the app’s PySceneDetect AdaptiveDetector defaults. Frame indexes were mapped to actual decoded timestamps.
- One run, six short exported clips, no exhaustive independently labeled reference set. No precision/recall/F1 claim or whole-game speed claim is supported. The comparison was sequential, so cache/order effects are possible.
- The original long videos were not used. Neither detector can recover action already absent from an exported clip.
- Raw results, prediction arrays, reproduction script and extra-transition contact sheet are in work/transnet-benchmark/.
