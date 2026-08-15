# Senior SRE Take-Home: Kubernetes Health Reporter

**Timebox:** 60–75 minutes. We mean it — we would rather see a well-reasoned partial
solution than a rushed complete one.
**AI:** allowed and expected. See *AI usage* below.
**Follow-up:** a 25-minute live session where you extend the tool on a call with us.

## Context

`health_reporter.py` is an existing tool that reads a `kubectl get ... -o json`
export and reports workloads that are not healthy. It was written quickly with AI
assistance, it runs, and its test suite passes.

It has never been validated against production data.

We are about to wire it into on-call alerting for our search platform. Your job is to
decide whether that is safe, fix what isn't, and tell us what you changed and why.

## Your task

1. **Review and fix `health_reporter.py`.** Run it against `sample_cluster.json`, which
   is a lightly-anonymised export from one of our clusters. Decide which of its outputs
   you believe. Fix what's wrong.
2. **Fix the tests too.** `tests/test_health_reporter.py` passes today. That does not
   mean it is correct.
3. **Keep the tool read-only.** It must never mutate cluster state.
4. **Satisfy both of these at once:**
   - It must not alert during a healthy rolling update or a deliberate scale-down.
     Waking someone at 03:00 for a normal deploy is a defect, not a nuisance.
   - It must alert within 5 minutes when a workload is genuinely degraded.

   If you conclude these cannot both be fully satisfied given the input we hand you,
   say so explicitly and describe what input you would need.
5. **Write up your reasoning** in `README.md` (template provided).

We have deliberately not given you a list of edge cases. Finding them is the exercise.

## Required output

For every workload you report:

- Namespace
- Workload kind
- Workload name
- Desired replicas
- Ready/available replicas
- Unavailable replicas
- Not-ready Pods, and the best reason available from the supplied data (Unknown is acceptable when the export does not contain enough information)
- Restart count or restart summary

## Interface contract

We run your tool automatically against additional cluster exports you have not seen, so
these must hold exactly:

**Exit codes**

| Code | Meaning |
| --- | --- |
| `0` | every workload inspected is healthy |
| `1` | at least one unhealthy workload was found |
| `2` | the input could not be inspected |

A crash traceback reaching the user is a failure regardless of exit code.

**`--json` output** — machine-readable mode, printed to stdout, nothing else on stdout:

```json
{
  "unhealthy": [
    {
      "namespace": "search-prod",
      "kind": "StatefulSet",
      "name": "search-index",
      "desired": 3,
      "ready": 2,
      "unavailable": 1,
      "restarts": 12,
      "notReadyPods": [
        {"name": "search-index-2", "phase": "Running", "reason": "CrashLoopBackOff", "restartCount": 12}
      ]
    }
  ]
}
```

You may add fields. You may add sections (for example, findings that don't fit the
"unhealthy workload" shape). Don't remove the ones above.

The export includes a top-level `capturedAt` timestamp. We added it so results are
reproducible; treat it as "now" if you need a notion of now.

## Deliverables

- The fixed tool.
- Tests, or test notes if you ran out of time. Tell us what you'd add next.
- Example output, committed.
- `README.md` covering:
  - **What was wrong.** One line per defect you found, with the consequence. If you
    found a defect you chose not to fix, say so and why.
  - **Decision log.** For each significant call, the alternative you rejected and why.
    We are more interested in this than in the code.
  - **Assumptions and limitations.** What does your tool miss? What would page falsely?
  - **Productionising it.** How would you run this as monitoring or in CI, and what
    would you change to make it safe to alert on?
  - **AI usage.** Which parts you used AI for, what it got wrong, and how you found out.

## AI usage

Use whatever tools you use at work — we do. We are not measuring whether you used AI.
We are measuring whether you can tell when it is wrong. 
Not using any will not be a positive point, but is a negative one

Two things we ask:

1. **Include your prompts or session transcript**, or a summary if it's long.
2. **Be specific about the failures.** "AI suggested X, which is wrong because Y, and I
   caught it by Z" is what we're looking for. If AI got everything right, say that — but
   note how you verified it rather than that you trusted it.

A submission whose reasoning the candidate cannot explain scores worse than a smaller
submission they can. The live session is where this shows up, so don't submit anything
you don't understand.

## Live session (25 min, after we review)

Bring your submission. We will hand you a cluster export you haven't seen and ask you
to make your tool handle it, then ask you to remove one of your own safeguards and
explain what breaks. Read-only, no cluster access needed, screen share.

## Evaluation

| Dimension | Weight |
| --- | --- |
| Kubernetes workload understanding | 25% |
| Correctness against hidden data (false positives weigh double) | 20% |
| Judgment and explanation of trade-offs | 20% |
| AI verification and debugging | 20% |
| Code quality and error handling | 15% |

## Submission

Repository link or archive: code, README, example output, tests or test notes, and your
AI transcript.
