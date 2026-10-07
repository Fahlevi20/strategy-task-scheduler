# Strategy Task Scheduler — Design

## Purpose and scope

Build a small, runnable Python demonstration from `context.md` for an interview exercise. The system accepts user-submitted task definitions, finds tasks due at a supplied time, simulates their actions, and limits each user's successful executions per calendar day. Keep it synchronous and in memory. Demonstrate separation of responsibilities, careful handling of failures, and verification with tests and linting rather than production infrastructure.

## Proposed approach

Use Python's standard library for the application and tests, plus Ruff for linting. Separate four responsibilities without adding a web framework, database, persistent job store, or worker queue:

- `Task`: a validated data model with a stable task ID, username, daily scheduled `HH:MM`, action name, target, and configurable `parameters` dictionary. Construct tasks from dictionary input. Reject malformed times, missing required fields, and unknown actions with clear errors.
- `QuotaManager`: register users with nonnegative daily quotas; track the number of **successful** tasks by username and date. Expose a quota check and record a success. Unknown users are rejected explicitly.
- `TaskExecutor`: map action names to callable simulated handlers (for example, `sync`, `backup`, and `delete`). Handlers log or return a simulated result; none touch the filesystem. Log action success or failure with task ID, username, and action. An action exception does not consume quota.
- `Scheduler`: hold registered tasks and run tasks matching the supplied date/time. In insertion order, skip successful task IDs already run on that date, check the user's quota, dispatch via the executor, and record a successful result. Log quota skips and errors; processing one bad task must not prevent other due tasks from running.

Callers pass `datetime` to `run_due` so tests do not depend on wall-clock timing. The clock's date determines the quota and duplicate-run keys; use naive local datetimes in this exercise and document that production deployments must choose a timezone. Tasks run daily at their configured minute. Calling `run_due` again on the same calendar day does not re-execute a task that already succeeded; a task that failed may be retried while due. A task is uniquely identified by its stable ID, so users can submit multiple simultaneous tasks, including identical actions and targets.

## Data flow

A small example entry point registers users and parses task dictionaries, then invokes `run_due` for a supplied time. The scheduler checks each due task's ID and quota, invokes its action handler, and records success only after a successful return. Log the outcome, and return structured per-task outcomes (success, already completed, quota exceeded, or failure) so tests and callers can inspect behavior without parsing logs.

This design is intentionally single-process and non-persistent. A restart clears quotas and completed-task IDs. Concurrent calls are out of scope: quota check and success recording are not atomic. Running missed minutes later is also out of scope; the caller is responsible for invoking `run_due` at the intended minute.

## Error handling and safety

Validate user quotas and task data at input boundaries. Unknown users, invalid action names, handler failures, and exhausted quotas produce clear, traceable logs or errors without incrementing usage. The `delete` handler is a **simulation**, never a real deletion. Configure logging at the example entry point, not during module import. Avoid swallowing programming errors silently; return a failure outcome with the exception logged when a handler fails.

## Verification and delivery

Test with the standard-library `unittest`: due versus non-due tasks, multiple tasks for one user in one minute, quota exhaustion, per-day reset, no duplicate successful execution on repeated calls, retry after a failed action, invalid inputs, and isolated handling of task failures. Run the example, the full test suite, and Ruff locally. Add a GitHub Actions workflow that installs Ruff and runs lint and tests on pushes and pull requests. A short README documents setup, commands, design decisions, limitations, and AI-assisted verification. Add a `.gitignore` for Python caches, virtual environments, local environment files, and tooling artifacts. The planned in-memory demonstration requires no credentials or environment variables, so do not create an empty `.env.example`; if credentials or required environment variables become necessary, add a sanitized `.env.example` documenting their names and never commit real secrets. Before pushing to `https://github.com/Fahlevi20/strategy-task-scheduler.git`, ask the user to test the code locally and review the results; do not claim CI passed until an actual GitHub Actions run succeeds.

## Alternatives considered

A single script with helper functions would be quicker but would not demonstrate the requested modular boundaries as clearly. A persistent queue, async workers, and external storage would support large deployments but are unnecessary for a simulated 30-minute assignment and introduce failure modes that the exercise does not require. The synchronous, in-memory approach provides a verifiable base that can be replaced with durable storage and atomic quota reservations if scale becomes necessary.
