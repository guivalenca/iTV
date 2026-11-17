# Local build review and resolution

The two Opus 5.5 High reviews examined the frozen initial change in
`.cache/review/build-v1/`: seven new files against an absent-file baseline. The
repository had no commits. Pre-existing skill files were excluded. The upstream
baseline was `8ec95131a9339df90d4dd0c2435e794ae192c19d`.

The reports describe that earlier snapshot. The parent subsequently applied the
corrections below and verified the resulting build; the consultants did not
review the corrected version a second time.

## Standards

The reviewer found two documented-standard violations: one medium and one low.

- The initial patch removed browser coverage for release parsing and
  acknowledgement while retaining the manual release check. The final patch
  removes the release-request and parsing implementation altogether. Tests now
  cover the retained behavior: no release requests at startup, on visibility
  changes, or on manual checks; cached releases cannot display an update command.
- Request logic and comments made obsolete by disabling automatic checks have
  been removed with that implementation.

Minor heuristic observations were considered separately. The unused SDK-download
return value and vague review reference are gone. The small duplicated version
regex and documented helper tuples remain; neither warrants another abstraction
in this build script. The cache-key literal in the test represents persisted
input the service must ignore.

Original report: [standards-review.md](../../.cache/review/build-v1/standards-review.md).

## Spec

The reviewer found five implementation issues: one medium and four low. All were
addressed:

1. Both automatic and manual release requests are disabled. Cached notices are
   ignored. The build rejects any compiled launcher file containing
   `api.github.com`.
2. Before rebuilding, the old receipt is archived under `.cache/receipts/` and
   removed from `dist/`. A new current receipt is written only after success.
3. The CLI comparison runs after patches. Tracked differences, unexpected source
   files, and Git errors stop the build.
4. A failed or interrupted first CLI installation cleans up only the new partial
   environment. An environment that existed before the invocation is preserved.
5. The receipt records the verified local SDK archive URL and SHA-512 when that
   archive is available. External SDKs are recorded without an archive claim.

The optional browser checks are documented and remain opt-in. Issue #1 exists and
was explicitly requested by the user; linking it is not an unapproved repository
creation, commit, or push.

Original report: [spec-review.md](../../.cache/review/build-v1/spec-review.md).

## Final verification

- Build, formatting, lint, and type checks passed.
- Node: 567 passed; component: 159 passed; packaged service: 13 passed.
- Targeted Python: 317 passed; host policy harness: 114 passed.
- Recovery/build guard tests: 6 passed.
- Browser: one passed on its first attempt; two passed on retry and were reported
  as flaky. This is not a clean first-attempt browser run.
- Package contents, Home/Watcher identities, source and patch hashes, helper
  manifests, installed recovery CLI, and the final receipt were checked.
- The existing recovery CLI package remained unchanged through the rebuild.

Final unsigned WGT SHA-256:
`7ff49d7ee634076c59d4065f52c06c2e3a2c55f4aba45a5b86e8399b77be5b8b`.

Standards: 2 documented findings, worst medium, resolved. Spec: 5 implementation
findings, worst medium, resolved. No remaining material finding was identified by
the parent. The TV proof had not been run at the time of these build reviews;
subsequent hardware results are recorded in [stock-proof.md](../stock-proof.md).
