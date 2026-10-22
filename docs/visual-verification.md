# Visual assistance in Auto Delivery

The Overview's **Visual environment** panel and the Agent use the same local
environment inspector. `lumon doctor --visual --json` exposes the same structured
report for an Agent or operator and forces a fresh check. Normal requests reuse a
30-second process-local cache. The report includes its observation timestamp;
different Lumon processes can have different observation times and tool paths.
Normal chat prompt checks run off the Agent event loop. In-flight steering uses
the last observation without waiting for a probe, so a publication hold is not
delayed by environment discovery. Visual work still explicitly refreshes first.

The inspector runs on the machine executing Lumon, with that process's environment.
For example, a launchd Agent and an interactive shell can have different PATHs.
Do not treat a Dashboard result from another process as proof that the Agent has
the same tools. The Agent checks again before starting visual work.

## What readiness means

- iOS: `xcrun simctl list --json` works, an iOS runtime is available and at least
  one available device belongs to it. A stopped device can still be ready.
- Android: SDK directory, executable ADB and emulator, working acceleration check,
  and a registered AVD with an existing system image matching the host architecture.
  SDK discovery respects `ANDROID_HOME` / `ANDROID_SDK_ROOT`; AVD discovery respects
  `ANDROID_AVD_HOME` / `ANDROID_USER_HOME`. Private experiment directories are not
  automatically searched. Neither ADB nor a device is started to inspect readiness.
- Web: Chrome or Chromium is installed. Automation-driver setup, the development
  server and the application's pages still need verification.
- Docker: the configured Docker connection answers `docker info`. This is separate
  from Web readiness; it does not verify any image, browser, Android runtime or
  local container. A remote Docker context remains remote.

Commands have a four-second timeout and independent platform probes run concurrently.
Tool stderr and raw JSON are never returned to the UI or Agent. Missing tools,
failed checks and unsupported platforms are distinct. The optional platform report
does not make `lumon doctor` fail for a machine that does not develop every platform.

Opening Overview does not boot devices, download images, install software, launch
applications or run project scripts. Details live behind the existing question-mark
popover. Refresh is explicit; switching Workspace discards in-flight UI responses.

`application_status: unverified` intentionally describes the limit of this passive
inspection. It is not a persisted verdict about prior deliveries. Application
build, startup, login, backend access and interaction evidence belong to each run.

## Implementation loop

The packaged Auto Delivery instructions require the implementation Agent to decide
whether the change affects UI or interaction. For applicable changes it follows the
Workspace's capabilities and works against the real Debug/development application:

1. Refresh prerequisites and read project guidance.
2. Prepare an isolated checkout and dedicated device/browser profile and ports.
3. Build/install Debug as needed, then use Metro/Fast Refresh or web HMR during edits.
4. Inspect affected screens and interactions and adjust the implementation.
5. Capture final redacted evidence with the source revision/diff fingerprint and
   actual build identity. A later change requires recapturing affected pages.
6. Follow saved publishing policy; where Workspace rules authorize Jira evidence,
   attach screenshots and add a Comment, verify the write by reading it back, then
   apply the Workspace's issue-transition rules.
7. Stop only resources owned by this run; keep source, evidence and reusable caches.

Native changes require a new build/install. A real application check is still needed
after a hot update. Backend waiting time is separate from emulator responsiveness.
No mandatory separate visual Agent or release build is introduced. Existing tests
and repository validation remain required. If an applicable visual check is blocked,
record the blocker instead of asserting that it passed. Non-UI work records why
visual validation does not apply.

## Workspace-owned guidance

Use existing `lumon/capabilities/*.md` documents for project-specific knowledge:
repository and package identity, build and dev-server commands, device selection,
authorized test environments and login shortcuts, pages to exercise and evidence
location. Keep credentials out of these files; refer to the approved account mechanism.
Technical Plan remains optional. MBPass commands, Jira status mappings and account
details are not added to Lumon's built-in workflow.

This change provides detection, discovery in Agent context, and workflow guidance.
It does not automatically install a toolchain or package the experiment's emulator
scripts as a production runner. It does not certify a fresh Mac, Web container,
authenticated app journey, or iOS build. Those checks must succeed in the selected
Workspace before their results can be claimed.
