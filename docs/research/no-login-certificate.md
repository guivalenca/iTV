# Installing the launcher without a Samsung sign-in: the Tizen SDK certificate

Date: 2026-11-15. Question: the Samsung account sign-in is temporarily rate-limited. Can we install the pinned launcher (`DclHome001`) on the U8600F (`UN50U8600FGXZD`, Tizen 9.0, `25_KSUE_UB_VOX`, `T-KSU2EFUABC-0090`) with a certificate that needs no Samsung account? Apps2Samsung v3.2.0 added one.

Scope: source and doc research only. There were no TV connections, no sign-in attempts, no certificate generation, no installs and no GitHub writes. Nothing was read from `~/.config/aerotizen` or the private baseline. Network access was limited to read-only GitHub API calls and fetching public documentation pages.

Labels:
- **Verified (source/doc):** read in pinned code or official documentation.
- **Reported:** a maintainer's own test or claim in an issue or PR. Not reproduced here.
- **Inference:** my reasoning from the above.
- **Unknown:** no evidence either way.

Shorthand:
- **[A]** = `https://github.com/Apps2Samsung/Apps2Samsung/blob/4b70ae5cadbd0fd55774615144f6ed91d340ab03/`, which is tag `v3.2.0`.
- **[S]** = `https://github.com/helalaou/AeroTizen/blob/8ec95131a9339df90d4dd0c2435e794ae192c19d/`, our pinned source.

---

## Bottom line

1. **Recommendation: wait for the Samsung certificate. Don't trial the SDK certificate with `DclHome001`.**
   - The SDK certificate has exactly one positive data point: a 2019 Tizen 5.0 set.
   - Samsung and Tizen documentation, and the Apps2Samsung FAQ, all say Tizen 7+ / Samsung devices need the Samsung certificate.
   - Nothing at all reports a Tizen 6+ result.
   - The likely outcome is a harmless refusal, which tells us little.
   - The unlikely outcome is worse: `DclHome001` gets installed under a throwaway author key. That locks future updates to that key or forces an uninstall. It also puts an unproven signing chain under Native Home.
2. **If the trial fails, it is safe. If it succeeds, it creates a commitment.**
   - A chain refusal (`[118, -12] … <-3>`) stops the install before anything is installed (Reported, Tizen 5.0).
   - Success would install the on-boot `DclHome001.Watcher` service, signed by a key that the Samsung-signed path can't update in place.
3. **This is ordinary SDK signing, not an account bypass.**
   - Tizen Studio's own Certificate Manager offers a "Tizen" profile that is created locally. Samsung's Apache-2.0 VS Code helper implements it.
   - It doesn't touch, retry or work around the Samsung sign-in. It needs no root or exploit, and uses the same Developer Mode `vd_appinstall` as the planned path.
   - So it is *permitted*. It just isn't *promising* on Tizen 9.
4. **If the user still wants the data point,** a separate throwaway probe package is a cleaner question than the real launcher. It keeps `DclHome001` untouched. It needs the user's explicit OK, and an uninstall of the probe if it is accepted, so it lies outside the constraints given for this task. The minimal steps are in the last section, for the record.

---

## 1. What the Apps2Samsung "Tizen certificate" is

**Verified (source):** [A]`Apps2Samsung.Core/Certificate/TizenLocalCertificateService.cs#L50-L168`. For a level (Public/Partner/Platform) it:
- generates an RSA-2048 key;
- issues the **author** certificate locally from the Tizen Studio "Tizen Developers CA", whose certificate and *private key* ship with the SDK. The certificate is valid 1 year, has a CN-only subject, `CA:false`, KU digitalSignature + keyEncipherment, EKU clientAuth + emailProtection, an SKI, and is signed with SHA-256;
- copies one of the SDK's **ready-made distributor signers** under a random profile password;
- writes `author.p12`, `distributor.p12` and `password.txt`.

It has no DUID, no network and no `device-profile.xml`.

**Two distributor generations** ([A]`…/TizenDistributorChain.cs#L9-L20`, [A]`…/TizenSdkAssets.cs#L36-L51`):
- **Legacy (2012, "Tizen Test CA"):** Public and Partner signers. **Expired since October 2022.**
- **New (2022, "Tizen Studio … CA Class"):** Public, Partner and Platform, valid to 2032.
- Public defaults to legacy.

**This mirrors Samsung's own tooling** (Verified, source):
- Samsung's Apache-2.0 [`webIDE-common-tizentv/lib/tizenCertificateManager.js`](https://github.com/Samsung/webIDE-common-tizentv/blob/dev/lib/tizenCertificateManager.js) (L20-L27, L126-L130) loads the same `certificates/developer/tizen-developer-ca-privatekey.pem` and the `sdk-public` / `sdk-partner` distributor signers from an installed Tizen Studio, and signs a locally generated author certificate with the CA key.
- The SDK hard-codes the CA key password and the signer password. They protect nothing and are not reproduced here.

**What the author signature proves.** The developer CA key is public, so anyone can mint an author certificate under it. The author signature then proves nothing about identity. It only pins the update key, and that is all we would rely on.

## 2. Evidence on which TVs accept it

| Source | What it says | Weight |
| --- | --- | --- |
| Apps2Samsung [#988](https://github.com/Apps2Samsung/Apps2Samsung/issues/988), maintainer comments 2026-11-04 | **Tizen 5.0 (2019):** the legacy Public signer → "install completed, app launches". Legacy Partner and all three 2022 signers → `install failed[118, -12] … Invalid certificate chain … <-3>`. The TV ignored the distributor's 2022 expiry. | Reported, one TV, one version |
| [PR #990](https://github.com/Apps2Samsung/Apps2Samsung/pull/990) | The same table. The CLI `--tizen-cert`, `--tizen-chain legacy\|new` path was proven end to end on that same Tizen 5.0 set. | Reported |
| [PR #992](https://github.com/Apps2Samsung/Apps2Samsung/pull/992) | The UI says "Some TVs accept it, others refuse it and say so". It was "not yet tried on a TV through the heads". An Automatic per-Tizen-version rule is deferred "once there are more data points". | Maintainer's own caveat |
| [PR #1011](https://github.com/Apps2Samsung/Apps2Samsung/pull/1011) | Warns that "retail TVs (Tizen 5.0 tested) refuse" the 2022 chain. | Reported |
| [v3.2.0 release notes](https://github.com/Apps2Samsung/Apps2Samsung/releases/tag/v3.2.0) (2026-11-09) | "When a TV refuses it, the app says so and offers Sign in with Samsung instead." | Vendor claim |
| [Apps2Samsung wiki FAQ](https://github.com/Apps2Samsung/Apps2Samsung/wiki/FAQ) | "Do I need a Samsung developer account? **Yes**, if you're installing on a Samsung Tizen TV with Tizen 7 or up." Still unchanged after v3.2.0. | Maintainer doc |
| Samsung, [Application Installation Policy](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-emulator/application-install-policy.html) | "Since Samsung TV Extension 7.0.1, only applications that have been signed with a **Samsung certificate** can be installed on the **TV Emulator**." | Official. Even Samsung's own emulator image dropped the Tizen chain |
| Samsung, [Creating Certificates](https://developer.samsung.com/smarttv/develop/getting-started/setting-up-sdk/creating-certificates.html) and [VS Code: Creating Certificates](https://developer.samsung.com/smarttv/develop/tools/additional-tools/vscode/creating-certificates.html) | "All applications must be signed with valid certificates." The prerequisites are a Samsung Developers Portal account and the target DUID. | Official |
| Tizen docs (Samsung/tizen-docs, updated 2026-08-13): [signing-certificates/index.md](https://github.com/Samsung/tizen-docs/blob/master/docs/application/dotnet/guides/concepts/signing-certificates/index.md) L3-L7, [creating-certificates.md](https://github.com/Samsung/tizen-docs/blob/master/docs/application/dotnet/guides/concepts/signing-certificates/creating-certificates.md) L27-L28 | "To install Tizen applications on Samsung Tizen devices, you must first register certificates containing the DUID." Choose **Samsung** to install on Samsung devices. Choose **Tizen** "if you want to use the emulator". | Official |
| Apps2Samsung permit logic, [A]`Apps2Samsung.Core/Sdb/TizenInstallSupport.cs#L38-L70` | A device-profile push is only needed on Tizen ≤ 4.0. "Newer TVs carry the authorization inside the re-signed package", meaning the DUID in a Samsung distributor certificate. The SDK distributor names no TV. | Maintainer's model. Tizen 5.0 accepting a DUID-less legacy signer shows it isn't strictly enforced there |
| AeroTizen issues (searched "tizen certificate", "certificate chain", "without samsung account") | No report of a Tizen SDK certificate on any model. Every model report (including [#183](https://github.com/helalaou/AeroTizen/issues/183), U8600F 75") used the Samsung certificate from `certs`. | Absence |

**Tizen 9 / U8600F: no primary evidence either way. Unknown.**

**Inference.** The weight of the evidence points to refusal on a 2025 Tizen 9 set:
- Every official source routes Samsung devices to the Samsung certificate.
- Samsung removed Tizen-chain acceptance even from its TV emulator.
- The only acceptance is a Tizen 5.0 set trusting a 2012 test root that newer images are likely to have dropped.

That is a likelihood, not a certainty. A chain refusal would surface as `[118, -12] … <-3>`.

## 3. Our package against this certificate

**Verified:**
- `dist/wgt/aerotizen-launcher-3.2.0.wgt` hashes to `7ff49d7e…77be5b8b`. It contains no signature files.
- Its `config.xml` declares `DclHome001.Home` and `DclHome001.Watcher` (`on-boot="true" auto-restart="true"`) and seven `tizen.org` privileges: internet, filesystem.read/write, application.launch/info, tv.window and tv.inputdevice ([S]`launcher/config.xml`).
- AeroTizen's own `certs` asks Samsung for `privilege_level="public"` ([S]`cli/src/aerotizen/certs.py#L145-L148`), and that is what worked on U8600F #183. So the app needs only **Public**.
- On Tizen 5.0, only the **legacy Public** SDK signer was accepted, which matches that level.
- Partner and Platform are irrelevant and were refused anyway.

**Certificate-chain details for our signer** (Verified, source):
- `signer._load_p12` keeps the leaf plus non-self-signed extras ([S]`cli/src/aerotizen/signer.py#L102-L106`). Roots are therefore not embedded.
- PR #992 says the accepted Tizen 5.0 signature also sent "the signer and its intermediate CA (the root is never sent)". So our signer's format matches in principle.
- `sign_wgt` reads exactly `author.p12`, `distributor.p12` and `password.txt` with one password ([S]`…/signer.py#L109-L114`), the same layout Apps2Samsung produces.

**The CLI blocks this path as is** (Verified, source):
- `_install_signed` exits unless `distributor.p12` exists in `~/.config/aerotizen/certs/<DUID>/`.
- It always pushes `device-profile.xml` before `vd_appinstall` ([S]`cli/src/aerotizen/cli.py#L262-L277`, [S]`cli/src/aerotizen/sdb.py#L412-L415`).
- An SDK profile has no device profile.
- So a trial would need a separate one-off script that reuses the frozen modules. Do **not** edit `dist/aerotizen-cli`, and do **not** put SDK files in the Samsung `certs/<DUID>` directory: `install` would pick them up silently.

**Native Home depends on the installed package actually running** (Verified, source):
- `home apply` launches AeroTizen and waits for the Watcher control service, protocol 1 ([S]`cli/src/aerotizen/home_control.py#L272-L320`, #L340-L351).
- So a successful *install* would not prove the SDK-signed package's service starts on boot, keeps its privileges, or passes `home apply`.
- Those would be new unknowns on top of the proven Samsung-signed path.

## 4. Risk of a bounded install trial with `DclHome001`

| Outcome | Effect | Risk |
| --- | --- | --- |
| Refused (`[118, -12] <-3>`), the likely case | Nothing installed (Reported for Tizen 5.0). A staged `.wgt` may remain in `sdk_tools`. Baseline untouched. | Low |
| Accepted | `DclHome001` installed with an SDK author key. The **Watcher starts at next boot** even if we never open the launcher (on-boot service). That is the same as the planned path, and the baseline is already saved. | See below |

**What happens after an acceptance:**
- **Update lock-in.** Tizen rejects an in-place update signed by a different author. AeroTizen's own guidance is not to run `certs --force` after install for this reason ([pinned-build-review](pinned-build-review.md) §"Untested"). Moving to the Samsung certificate later means uninstalling `DclHome001`. That is safe only *before* `home apply`, and it is an uninstall the brief rules out.
- **Expiry.**
  - The SDK's Tizen Developers CA **expires 2027-01-01** (Reported, #988). That is about 6 weeks away.
  - The author certificate lasts 1 year.
  - The Tizen 5.0 set ignored *distributor* expiry. Whether Tizen 9 checks *author/CA* validity at update time is **Unknown**.
  - Phase 2 updates of our launcher could therefore stop working while Native Home is active. Recovering would then mean `home restore`, an uninstall, and a re-install with Samsung signing.
- **Unproven under Native Home.** The proof on this model line (#183) used Samsung signing.

**Not needed, not done** (Verified): root, `debloat`, firmware changes, service menu, package-ID changes or anything that interacts with the Samsung account. The trial is ordinary Developer Mode SDB plus `vd_appinstall`.

**Conclusion:**
- The *failure* case is low-risk but low-value: it confirms what the docs already say.
- The *success* case trades a few hours of waiting for a fragile, hard-to-reverse signing identity on the Home app.

So it is not worth it with `DclHome001`.

## 5. Provenance and licensing of the SDK signing assets

**Verified (doc):**
- Apps2Samsung is MIT ([A]`LICENSE`). Note that GitHub's license detector shows GPL-3.0 for the repository, so check `LICENSE` itself.
- Its [NOTICE.md](https://github.com/Apps2Samsung/Apps2Samsung/blob/4b70ae5cadbd0fd55774615144f6ed91d340ab03/NOTICE.md) (§"Tizen SDK certificate-generator files") says the developer CA cert and key and the five distributor `.p12` files are redistributed **unmodified** from Tizen Studio's `certificate-generator`. They are "the property of Samsung Electronics Co., Ltd. / the Tizen project", "not covered by the Apps2Samsung MIT license", with no license grant stated.
- Samsung's Apache-2.0 helper reads these files from an installed Tizen Studio, but does not ship them.

**Inference:**
- Using them locally to sign for our own TV is what the SDK is for.
- **Don't commit or redistribute them** in our repo.
- For stronger provenance, take them from an official Tizen Studio `certificate-generator` rather than from Apps2Samsung, or compare hashes against it. That means downloading Samsung's SDK, which is a new tool install and needs the user's approval.

## 6. If the user explicitly wants the data point anyway

This is not recommended with `DclHome001`. A throwaway probe answers the same chain question. Get explicit approval first. Nothing here was executed.

1. **Assets.**
   - Fetch three files from Apps2Samsung at commit `4b70ae5c…` (`Apps2Samsung.Core/Certificate/TizenSdk/`): `tizen-developer-ca.cer`, `tizen-developer-ca-privatekey.pem` and `tizen-distributor-signer-public-legacy.p12`.
   - Treat them as untrusted data in a new empty directory and record their SHA-256.
   - Do not install Apps2Samsung itself.
2. **Profile.**
   - Write the profile to a new directory such as `~/.config/itv/tizen-sdk-cert/` (`0700`), never `~/.config/aerotizen/certs/<DUID>/`.
   - Use a small script with `cryptography` that reproduces [A]`TizenLocalCertificateService.cs#L117-L168`: an author certificate issued by the developer CA, and the legacy Public signer key and chain repacked under one random password.
   - Write `author.p12`, `distributor.p12` and `password.txt`.
3. **Sign.**
   - Sign with the frozen module, `aerotizen.signer.sign_wgt(<input>, <scratch>/signed.wgt, <cert dir>)`, run by `dist/aerotizen-cli`'s interpreter without modifying that environment.
   - The input should be a minimal probe `.wgt` with its own package ID, public privileges only and no service. With `DclHome001` instead, every lock-in caveat in §4 applies.
4. **Install.**
   - Use a one-off script: `SdbSession.install(app_id, bytes, tool_path)`, then `cli.verify_install`.
   - Push **no** `device-profile.xml`. Do not launch anything and run no `home` command.
   - Use `--tv <IP>`, with NordVPN off.
5. **Read the result.**
   - `[118, -12] … <-3>` means this TV refuses the SDK chain. Stop and wait for the Samsung sign-in. Optionally report the data point on Apps2Samsung #988; that is a GitHub write, so ask first.
   - Acceptance means the probe is installed. Leave it unopened, decide with the user, and remove it later from the Apps menu. It is not the Home app, so that is safe.

## Uncertainties

- Tizen 9 acceptance or refusal of the legacy Public chain is **untested anywhere** I could find.
- Whether Tizen 9 checks author or developer-CA validity at install or update time is unknown, given the CA expires 2027-01-01.
- Whether an SDK-signed web service (`DclHome001.Watcher`) gets the same runtime behaviour as a Samsung-Public-signed one on Tizen 9 is unknown.
- The licensing status of redistributing the SDK files is unclear (no grant stated). Local use is low-concern.
- The Samsung pages fetched carry no visible date. The Tizen docs source was last updated 2026-08-13.
