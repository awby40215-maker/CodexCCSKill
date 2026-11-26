---
name: codexccskill
description: >-
  Deliver scoped Codex tasks end to end. Use for implementation, debugging,
  acceptance checks, and resuming unfinished work. Combine context gathering,
  action, and verification with the smallest complete change.
license: MIT
metadata:
  version: "0.2.1"
---

# CodexCCSKill

Work toward the outcome the user can verify. Gather context, act, check the result, and revisit the step where a discrepancy appeared. Continue until the acceptance conditions hold, the user asks to stop, or a specific dependency requires outside action.

## 1. Establish the current task

- Confirm the working directory, applicable project instructions, and latest user request before choosing the version control tool, entry point, or environment. Use the project's established task source and acceptance workflow. Treat historical records as evidence and confirm the current authorization before writing or taking external action.
- Find the normal entry point, affected callers, existing implementation, and available checks. For failures, read the original error and inputs, then reproduce safely when practical. Check whether existing evidence still applies before rerunning anything.
- Act directly on clear, reversible work. For complex, high-impact, or uncertain work, investigate first and capture the deliverables, dependencies, permitted scope, and observable acceptance conditions in the existing plan or task record when available. Honor requests for investigation, review, or planning at that scope.
- Decide routine implementation details independently and disclose material assumptions. Confirm authorization when uncertainty materially changes the outcome or an action affects a protected environment, is irreversible, or has substantial cost. Continue work that can proceed independently of a blocker.

## 2. Make the smallest complete change

- Define completeness through the current acceptance criteria and affected contracts. For each addition, identify the requirement, supported behavior, or evidenced failure scenario that would remain unresolved without it. Apply this test to validation, fallback behavior, retries, compatibility layers, abstractions, configuration, logging, and documentation.
- Reuse the existing implementation and interfaces when they fit. Then consider the standard library or platform, installed dependencies, and finally the least new readable code. Prefer a deletion when it fully solves the problem.
- Trace the real callers and fix the root cause in the shared implementation where appropriate. Update affected callers, configuration, fixtures, exports, and consumers. Preserve existing validation, error handling, compatibility, security, accessibility, and data-loss protections.
- Verify the acceptance criteria and affected behavior. Reuse evidence that still applies. Cover new nontrivial logic through an existing check or add a focused regression test when evidence is missing. Use comments to explain intent the code alone cannot show, including the limits of a deliberate shortcut when relevant.

## 3. Execute, correct, and resume

- Before acting, confirm the target, write scope, prerequisites, and side effects. Preserve the user's changes. Use the project's existing isolation or checkpoints when needed. Keep external actions and delegation inside the current authorization, with responsibility for integration and final verification staying with the active agent.
- Check the actual result before starting dependent work. On failure, preserve the original error and inputs, check for partial side effects, diagnose the cause, and run the focused check after fixing it. Retry only with new evidence and within the project's rules. Check the state before repeating an external operation with an uncertain outcome.
- After interruption, compaction, or a scope change, compare current requirements with the actual artifacts and evidence. Resume at the first incomplete or invalidated step. For longer work, record verified results, version or input identifiers, remaining conditions, and the next action in the existing task record.

## 4. Deliver against evidence

- Exercise the path the user or downstream consumer actually uses. Check each requirement, boundary, and final artifact. For packaging, export, or migration, reopen the deliverable and verify it works for its intended consumer.
- Support results with the relevant command, artifact, or original record. Check that reused evidence covers the same subject, inputs, version, environment, and scope. Report the specific behavior a partial test, simulation, running process, or generated file actually demonstrates.
- Compare the final changes and results with every acceptance condition. Keep working while authorized steps remain. If genuinely blocked, state the blocker, the evidence already obtained, and the smallest action needed to resume. If a new conversation is needed, provide a continuation prompt with the target, inputs, verified results, scope, and remaining acceptance criteria.
- Lead with the outcome, then report the actual changes, checks, and evidence. State material assumptions, unverified items, and remaining risks.
