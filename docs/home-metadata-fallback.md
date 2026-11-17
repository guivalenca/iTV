# Empty Samsung model metadata

During the physical restore/reapply proof on 2026-11-16, Samsung's HTTP API returned
`modelName: ""`. The pinned CLI correctly refused Home apply before writing anything.
Reopening AeroTizen did not repair the field. The live SDB connection still reported
`device::UN50U8600FGXZD::0`, matching the immutable original backup. The HTTP platform,
SDK identity, native firmware build, architecture and Tizen version also matched.

This identifies the failing input; it does not establish why Samsung omitted it.
The symptom matches the previously identified upstream #213 report.

`scripts/aerotizen-home.py` wraps the frozen CLI in the current Python process.
It changes no installed CLI, helper, launcher or original backup files. All original
Home preflight checks, native helper checks and transaction handling still run.

The additional path runs only for the exact empty-string HTTP model. It requires:

- a valid original backup bound to the hash of the live SDK DUID;
- a live SDB banner whose model exactly equals the saved model;
- a nonempty live HTTP platform exactly equal to the saved platform;
- the same SDK DUID before and after resolving the model.

Only the model field is filled, from the live banner. Evidence records its source.
A nonempty model is never replaced. Missing/null/malformed metadata is not repaired.
There is no fallback for creating the first original backup. The pinned CLI's
existing HTTP-offline recovery path is otherwise unchanged.
With an existing valid original backup, `home backup --output NEW_PATH` can export
an additional baseline using the resolved metadata. That writes a new file;
it does not replace the existing original. Exporting new baselines is unnecessary
for the current recovery procedure.

Run from the project directory with the frozen environment:

```sh
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv TV_IP home status --json
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv TV_IP home apply --yes
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv TV_IP home restore --backup PATH/original-home.json --yes
```

The normal safety rules apply: restore before uninstalling, preserve the complete
backup folder including transactions, retain signing certificates, and keep firmware
unchanged. The recovery ZIP includes this wrapper and this document alongside the
unchanged portable CLI wheel.

Validation: the original read-only `_check_preflight` failed with only `model`
different. The regression test failed against the pass-through wrapper with the
same error. After the fix, 15 metadata tests and 6 existing build guard tests pass
using the sealed CLI. These exercise the real preflight refusal for changed identity,
model, firmware, architecture and OS, plus invalid/absent backups, bad banners,
platform mismatch, explicit recovery paths, and identity changes during resolution.
The real CLI routing is exercised with the TV session and writer mocked: both
apply and restore receive guarded metadata, refusal happens before the writer,
and the original function is restored even when the CLI exits with an error.

Opus 5.5 High reviewed the wrapper, call sites, tests and recovery packaging and
reported no blocking findings. It also confirmed that the included wheel's core
CLI modules match the sealed environment. Its nonblocking coverage and documentation
notes were addressed locally; physical reapply and ZIP manifest checks remain
separate from unit coverage.

Review and physical reapply results are recorded in the stock proof report once
complete; local tests alone do not establish the final TV state.
