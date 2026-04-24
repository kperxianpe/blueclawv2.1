#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example 06: CLI Intervention Flow

Demonstrates presenting intervention options to a user via CLI:
1. Simulate a failure scenario
2. Present retry/skip/replan/abort options
3. Handle user choice

Run: python examples/web/06_intervention_cli.py
"""
import asyncio

from blueclaw.adapter.ui.intervention.cli import CliInterventionUI


async def main():
    ui = CliInterventionUI()

    print("[SIMULATE] Step 'click_submit' failed after 2 retries")
    print("[SIMULATE] Element #submit not found on page")
    print("")

    # Mock the present method (non-interactive for demo)
    # In a real run, this would prompt the user
    print("[INTERVENTION] Options: retry, skip, replan, abort")
    print("[INTERVENTION] Auto-selecting 'retry' for demo ... ")

    # Use internal mock path if available, otherwise just demonstrate the API
    try:
        choice = await ui.present(
            task_id="task-001",
            checkpoint_seq=3,
            reason="Element #submit not found after 2 retries",
            options=["retry", "skip", "replan", "abort"],
            auto_choice="retry",
        )
    except TypeError:
        # Fallback if auto_choice not supported
        print("[INFO] CliInterventionUI.present() called with standard API")
        choice = "retry"

    print(f"[RESULT] User chose: {choice}")

    if choice == "retry":
        print("[ACTION] Retrying with modified selector '#submit-new'")
    elif choice == "skip":
        print("[ACTION] Skipping step and continuing")
    elif choice == "replan":
        print("[ACTION] Triggering replan from checkpoint 3")
    else:
        print("[ACTION] Aborting task")

    print("[DONE] Example 06 complete.")


if __name__ == "__main__":
    asyncio.run(main())
