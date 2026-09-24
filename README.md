# YAAP KernelSU LKM builder

This repository builds four loadable KernelSU modules against the YAAP OnePlus SM8650 `seventeen` kernel:

- `kernelsu.ko`: official KernelSU
- `kernelsu_next.ko`: KernelSU-Next
- `resukisu.ko`: ReSukiSU
- `backslashxx.ko`: `backslashxx/KernelSU`

The workflow is `.github/workflows/build-lkm.yml`. Start it with **Actions -> Build YAAP KernelSU LKM -> Run workflow**. It follows the latest commits on the configured YAAP and KSU branches, records every resolved SHA in the release manifest, and uses the Floran clang-r596125 toolchain. The generated release contains debug-stripped `.ko` files, `manifest.json`, `SHA256SUMS` and the effective YAAP config.

## Loading the module

Use the Manager belonging to the selected KernelSU fork and choose its LKM/module installation flow. Alternatively, upload the matching raw `.ko` in `E:\Code\ksupatcher` and use ksupatcher to patch `init_boot.img`. Do not install more than one of the four modules in the same boot image.

These are kernel modules, not Manager APKs. The Manager must match the fork's protocol and package/signature expectations.

## Compatibility requirements

The module must be loaded by a kernel built from the same YAAP source revision, effective `.config`, generated headers, `Module.symvers`, compiler family and module-signature policy. A module built here is not a generic GKI module.

The default workflow input disables `CONFIG_MODULE_SIG_PROTECT` in the build configuration. This does not change an already-installed boot kernel: if that kernel enforces signatures, these unsigned LKMs cannot load. Choosing `y` does not sign the modules; a device-trusted signing path would be required. The workflow rejects `CONFIG_MODULE_SIG_ALL=y` because stripping a signed module invalidates its signature.

ReSukiSU is built with its tracepoint hook and with manual hook/SUSFS disabled. The YAAP source is not modified with the simonpunk SUSFS patch, so enabling ReSukiSU manual hook or SUSFS would not be a valid default for this tree.

The modules repository is cloned from the latest `seventeen` revision for provenance. Its Android build metadata is not merged into the standalone kernel build; the LKM is compiled against the latest YAAP kernel tree and its exported symbols.

## Why this is not the DDK workflow

The upstream DDK workflows run inside a prebuilt `ddk-min` image against a stock
KMI source tree. They are useful when the target kernel has the expected GKI ABI,
but they do not build YAAP's vendor tree or its external modules. YAAP's
`drivers/base/touchpanel_notify` path is a symlink into the sibling modules tree,
so this workflow checks out both trees with those exact names, builds YAAP first,
and only then builds each external LKM from the resulting headers and
`Module.symvers`. This is required for YAAP's non-standard exported-symbol set.
Before the kernel build it restores YAAP's `modpost` export checks for KernelSU
modules, so their `__versions` tables contain CRCs from this kernel build. The
workflow stops instead of publishing a module that refers to an unexported
symbol or has an empty version table. It strips debug information only after
linking, then rechecks the module metadata and versions.
An undefined-symbol failure requires an LKM-compatible fork or a matching boot
kernel that exports the required symbol; suppressing `modpost` cannot make the
raw `.ko` loadable.

The workflow also rejects configurations without `MODULES`, `KALLSYMS`, or
`KALLSYMS_ALL`, and rejects `CONFIG_TRIM_UNUSED_KSYMS`, because those settings
cannot produce a generally loadable KernelSU LKM. Every source clone first
resolves `refs/heads/<branch>` with `git ls-remote` and verifies the checked-out
commit, so each run uses the current tip of the selected YAAP and KernelSU
branches. The workflow also applies a narrow compatibility fix for the current
YAAP `certs/extract-cert.c` `key_pass` declaration bug. The other fixes address
the toolchain `clang` directory mis-detection, the YAAP modules symlink, missing
`modules_prepare`, and ReSukiSU's multi-manager tracepoint configuration.
