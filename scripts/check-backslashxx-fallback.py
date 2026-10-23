#!/usr/bin/env python3
"""Verify upstream's per-syscall ARM64 sucompat fallback protection."""

import re
import sys
from pathlib import Path


def check_fallback(source: str) -> None:
    # Commented-out guards must not satisfy the checks.
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    match = re.search(
        r"#if LINUX_VERSION_CODE >= KERNEL_VERSION\(3, 14, 0\)\s*"
        r"static int bl_hook_execve\(void \*data\)\s*\{(.*?)\n\}\s*#else",
        source, re.S,
    )
    if not match:
        raise ValueError("unrecognized ARM64 bl_hook_execve layout")
    body = match.group(1)
    for result in ("ret", "ret2"):
        if not re.search(rf"\bint {result} = -ENOENT;", body):
            raise ValueError(f"{result} must default to -ENOENT")

    # Check the assignment, guard, and restore together, not just a nearby if.
    # All native/compat paths must keep their fallback when inline patching fails.
    guarded_count = 0
    for abi in ("aarch64", "armeabi"):
        table = "sys_call_table" if abi == "aarch64" else "compat_sys_call_table"
        for handler in ("do_execveat_common", "do_execve_file", "do_execve_common"):
            calls = ("execve",) if handler == "do_execve_common" else ("execve", "execveat")
            for call in calls:
                result, site = ("ret2", "target_callsite2") if call == "execveat" else ("ret", "target_callsite")
                assignment = (
                    f"{result} = arm64_b_or_bl_patch({site}, ksu_get_ksym_size32({site}), "
                    f"symbol_addr, (uintptr_t)&ksu_{handler});"
                )
                restore = (
                    f"restore_syscall((void *)&{abi}_{call}, __{abi.upper()}_{call}, "
                    f"(void *)hook_{abi}_{call}, (void *){table});"
                )
                pattern = (
                    r"\b" + re.escape(assignment)
                    + r"\s*pr_info\([^;]+;\s*"
                    + re.escape(f"if (!{result})") + r"\s*" + re.escape(restore)
                )
                if len(re.findall(pattern, body)) != 1:
                    raise ValueError(f"unrecognized {abi} {call} guard for {handler}")
                guarded_count += 1
    if len(re.findall(r"\brestore_syscall\s*\(", body)) != guarded_count:
        raise ValueError("unexpected syscall restoration; refusing to skip compatibility patch")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} SOURCE_FILE", file=sys.stderr)
        return 2
    try:
        check_fallback(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"Unsupported backslashxx sucompat fallback: {error}", file=sys.stderr)
        return 1
    print("Verified upstream per-syscall sucompat fallback; legacy patch is unnecessary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
