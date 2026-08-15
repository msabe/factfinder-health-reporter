# Submission — Senior SRE Health Reporter

> Replace this template with your own content. Keep the headings; we grade against them.
> Bullets, not essays. If you ran out of time on a section, write what you would have
> done — that scores better than silence.

## How to run

```
python3 health_reporter.py sample_cluster.json
python3 health_reporter.py sample_cluster.json --json
python3 -m pytest tests/ -v
```

## Example output

<!-- Paste the real output of your tool against sample_cluster.json. -->

```
```

## What was wrong

<!--
One line per defect: what it was, and what it would have done to us in production.
Include defects you found but chose not to fix, and say why.
-->

| # | Defect | Consequence | Fixed? |
| --- | --- | --- | --- |
|  |  |  |  |

## Decision log

<!--
The section we read most carefully. For each significant decision: what you chose, what
you rejected. Include the ones you're unsure about.
-->

| Decision | Chose | Rejected |
| --- | --- | --- |
|  |  |  |

## Rolling updates vs. real outages

<!--
How does your tool tell a healthy deploy from a degraded workload? If the input we gave
you cannot support that distinction, say so and describe what you would need.
-->

## Assumptions and limitations

<!-- What does your tool miss? What would page falsely? Where is it guessing? -->

## Productionising

<!--
How would you run this as monitoring or in CI? What changes before it's allowed to page
a human? Consider: where it runs, what it reads, RBAC, cardinality, flapping,
what the alert actually says to the person woken up.
-->

## AI usage and verification

**What I used AI for:**

**What it got wrong:**

<!-- Be specific: the claim, why it was wrong, how you caught it. -->

**How I verified the parts that were right:**

**Transcript:** <!-- link, file, or summary -->

## What I'd do with more time
