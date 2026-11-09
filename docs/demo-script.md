# Functional recording script · target 2:40

This is a plan for a real screen recording, **not an existing recording or URL**. Record the host CLI and actual generated report. Avoid terminal history or paths containing private information. No QNX boot footage, SDK install, account, or physical device is needed for the host-tool demonstration. Use original narration, no unlicensed music.

| Time | Real action | Suggested narration |
| --- | --- | --- |
| 0:00–0:20 | Show README scope and the before fixture | “Boot Order Atlas reviews QNX 8 startup order on a host. These original fictional services illustrate declared dependencies; this is not a recorded QNX boot.” |
| 0:20–0:45 | Open `examples/serial-contract.json`, highlight panel requirements and foreground declarations | “The resource model is explicit. Atlas does not guess which device a program provides or whether a foreground driver detaches.” |
| 0:45–1:15 | Run the comparison command below; open the generated HTML | “The original starts the panel before its resource waits. The report links both warnings to source lines.” |
| 1:15–1:45 | Show the after timeline, added wait lines and conditional requirement states | “The revised version adds two finite path waits before the panel. The warnings disappear in this model, but `stat()` checks can time out and never prove service health.” |
| 1:45–2:10 | Run cycle example; show contract cycle and provider-order finding | “A contradictory declaration is reported as a contract cycle, not asserted to be a measured OS deadlock.” |
| 2:10–2:30 | Run boundary example; show inherited external wait and shell coverage gaps | “Unknown or out-of-scope syntax remains visible. External commands are not silently assigned internal semantics.” |
| 2:30–2:40 | Show verification result and scope caveat | “The source, tests and offline report are reproducible. Real target correctness still requires a licensed build and appropriate QNX validation.” |

```sh
python3 -m boot_order_atlas compare examples/serial-before.build examples/serial-after.build \
  --contract examples/serial-contract.json \
  --json output/demo.json --html output/demo.html
python3 -m boot_order_atlas analyze examples/cycle.build \
  --contract examples/cycle-contract.json
python3 -m boot_order_atlas analyze examples/boundaries.build \
  --contract examples/empty-contract.json
sh scripts/verify.sh
```

Upload only the resulting real recording after review. The official requirement is a public YouTube video shorter than three minutes; a draft script or local artifact does not satisfy it.
