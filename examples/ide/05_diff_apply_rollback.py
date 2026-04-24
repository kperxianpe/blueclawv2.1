#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 05: Diff Apply and Rollback

Demonstrates:
1. Create a file
2. Parse and apply a unified diff
3. Verify the change
4. Rollback to pre-apply state

Run: python examples/ide/05_diff_apply_rollback.py
"""
import os
import tempfile

from blueclaw.adapter.ide.applier import IncrementApplier
from blueclaw.adapter.ide.models import FileDiff, DiffHunk


def main():
    tmpdir = tempfile.mkdtemp()
    print(f"[INFO] Working in: {tmpdir}")

    # Initialize git
    os.system(f"cd \"{tmpdir}\" && git init -q")
    os.system(f"cd \"{tmpdir}\" && git config user.email \"demo@blueclaw.ai\"")
    os.system(f"cd \"{tmpdir}\" && git config user.name \"Demo\"")

    # Create original file
    original = "def greet():\n    return 'hello'\n"
    file_path = os.path.join(tmpdir, "greet.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(original)

    os.system(f"cd \"{tmpdir}\" && git add . && git commit -q -m 'init'")

    # Build diff
    diff = FileDiff(
        file_path="greet.py",
        hunks=[
            DiffHunk(
                old_start=1, old_lines=2,
                new_start=1, new_lines=3,
                lines=[
                    " def greet(name='world'):",
                    "-    return 'hello'",
                    "+    return f'hello, {name}'",
                ],
            )
        ],
    )

    applier = IncrementApplier(project_path=tmpdir)

    print("[RUN] Applying diff ... ", end="", flush=True)
    result = applier.apply_diffs([diff], auto_commit=True, commit_message="feat: add name param")
    print("OK" if result.success else f"FAIL ({result.error})")

    if result.success:
        print(f"[RESULT] Commit: {result.commit_hash[:8] if result.commit_hash else 'N/A'}")
        print(f"[RESULT] Files changed: {result.files_changed}")

        # Verify content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"[VERIFY] Content after apply:\n{content}")

        # Rollback
        print("[RUN] Rolling back ... ", end="", flush=True)
        rollback = applier.rollback(result.pre_apply_head)
        print("OK" if rollback.success else f"FAIL ({rollback.error})")

        with open(file_path, "r", encoding="utf-8") as f:
            content_after = f.read()
        print(f"[VERIFY] Content after rollback:\n{content_after}")

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[DONE] Example 05 complete.")


if __name__ == "__main__":
    main()
