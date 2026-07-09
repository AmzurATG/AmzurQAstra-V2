# Concurrent Test Execution by User Story - Implementation Plan

## Objective
Enable concurrent functional test execution using a worker pool, while preserving stable behavior and clear observability.

Key goals:
- Improve total execution time for bulk runs.
- Partition work logically by user story.
- Preserve login/session reuse where possible.
- Keep backward compatibility with current sequential execution.

## Current Baseline
- Test cases can already be selected by explicit IDs when creating a run.
- Test cases already include user_story_id and can be filtered by it.
- Execution currently runs one test case at a time in a single loop.
- Progress payload currently represents one active test case at a time.

## Proposed Execution Model
Use a worker-pool strategy:
- max_concurrency controls number of workers.
- Each worker owns one persistent browser session.
- Workers execute assigned test cases sequentially.
- Workers run in parallel with each other.
- Test cases are grouped primarily by user_story_id.

Why this model:
- Avoids unsafe concurrent use of one shared browser context.
- Reduces repeated logins compared to per-test browser creation.
- Fits current architecture with incremental changes.

## Work Partitioning Strategy
Primary partition key:
- user_story_id

Rules:
- Group all selected test cases by user_story_id.
- Place null user_story_id cases into a dedicated fallback bucket.
- Preserve original client-selected order inside each story group.
- Build worker assignments using load balancing:
  - First pass: assign entire groups to least-loaded worker.
  - Load metric: number of test cases (phase 1), optionally weighted by step count later.

Optional later improvement:
- Split oversized story groups if one story dominates total load.

## Compatibility and Defaults
- Default max_concurrency = 1.
- Existing behavior remains unchanged unless explicitly increased.
- Existing request payloads remain valid.

## API and Schema Changes
### Backend request schema
Add optional field:
- max_concurrency: int = 1

Validation:
- min 1
- max configurable cap (recommended 5 initially)

### Persistence
Persist effective concurrency in run config for traceability.

### Frontend payload
Extend run creation payload to optionally send max_concurrency.

## Backend Service Design
Target service:
- test execution service

Planned refactor:
1. Keep existing create_run behavior for result row provisioning.
2. Build ordered runnable list from run results and test case map.
3. Partition runnable list by user story.
4. Build worker queues based on max_concurrency.
5. Launch worker tasks concurrently with asyncio.gather.
6. Each worker:
   - Creates/owns a persistent browser context.
   - Executes its queue sequentially using existing runner.
   - Commits per-test result updates safely.
   - Cleans up browser context in finally block.
7. Aggregate final run status after all workers finish.

Database safety:
- Do not share one AsyncSession across concurrent workers.
- Use separate session per worker for updates, or serialize DB write section with a lock.
- Preferred: per-worker session for clearer isolation.

Cancellation behavior:
- Keep existing run-level cancel signal.
- Workers should check cancellation before starting each case and skip remaining queued items.

## Progress Model Evolution
Current payload is single-active-case oriented.

Phase 1 (minimal UI change):
- Keep existing top-level fields for backward compatibility.
- Continue completed_results and logs updates.
- Track aggregate counts accurately.
- Set current_test_case_title and current_step_info to latest worker event.

Phase 2 (enhanced UI):
Add optional field:
- active_workers: [{ worker_id, test_case_id, title, step_info, status }]

UI can then display true concurrent activity.

## Login and Browser Session Behavior
- Sequential mode (max_concurrency=1): single login reused across all selected tests.
- Concurrent mode (max_concurrency>1): one login per worker session.
- This is expected and safer than sharing one browser among concurrent tasks.

## Failure Handling
Per-test failure:
- Mark test result failed or error.
- Continue worker queue unless cancellation requested.

Worker-level crash:
- Log worker error.
- Mark in-progress item as error if needed.
- Continue or stop based on run-level policy (phase 1: continue other workers).

Run-level terminal state:
- passed if all completed and no failures/errors.
- failed if any failed/error.
- cancelled if cancellation triggered and remaining items skipped.

## Observability and Logging
Add structured logs with:
- run_id
- worker_id
- test_case_id
- user_story_id
- event (start, step, pass, fail, cancel, cleanup)

This improves debugging for concurrent runs.

## Testing Plan
Unit and integration tests to add:
1. Partitioning correctness by user_story_id.
2. Deterministic assignment when max_concurrency=1.
3. Multi-worker completion with mixed pass/fail outcomes.
4. Cancellation mid-run skips remaining queued items.
5. Progress payload remains valid for existing consumers.
6. No duplicate execution of same test_result.
7. DB updates remain consistent under concurrency.

Manual validation:
1. max_concurrency=1 behaves exactly like current version.
2. max_concurrency=2 or 3 executes visibly in parallel when headed.
3. Final counts and result details match executed set.

## Rollout Plan
Phase A:
- Backend schema + service implementation with default max_concurrency=1.
- Keep frontend unchanged (field optional).

Phase B:
- Frontend control for worker count in run modal/page.
- Basic guardrails and helper text.

Phase C:
- Enhanced multi-worker progress UI (active workers list).

## Risks and Mitigations
Risk: DB session contention.
- Mitigation: per-worker DB session isolation.

Risk: Browser resource saturation.
- Mitigation: enforce max cap and recommend small defaults.

Risk: Progress UI confusion during concurrency.
- Mitigation: phase 1 compatibility fields plus phase 2 active_workers model.

Risk: Uneven load by story size.
- Mitigation: least-loaded worker assignment and optional weighted balancing.

## Acceptance Criteria
1. With max_concurrency=1, behavior matches current sequential execution.
2. With max_concurrency>1, tests execute concurrently across workers.
3. No test case executes more than once in a run.
4. Final run totals and statuses are accurate.
5. Cancellation reliably stops remaining queued execution.
6. Existing polling endpoint remains backward compatible.

## Implementation Order (Recommended)
1. Add schema and type support for max_concurrency.
2. Implement partition and worker assignment helpers.
3. Refactor execution loop into worker-based orchestration.
4. Add per-worker DB session handling.
5. Preserve and validate progress payload compatibility.
6. Add tests.
7. Add frontend worker-count control.
8. Add enhanced active worker progress view.
