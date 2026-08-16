# Submission — Senior SRE Health Reporter

> Replace this template with your own content. Keep the headings; we grade against them.
> Bullets, not essays. If you ran out of time on a section, write what you would have
> done — that scores better than silence.

## How to run

```
python health_reporter.py sample_cluster.json
python health_reporter.py sample_cluster.json --json
python -m pytest test_health_reporter.py -v
```

## Example output

Normal output:
```text
search-prod Deployment search-api-canary: 0/1 ready
search-prod StatefulSet search-index: 2/3 ready
platform Deployment metrics-adapter: 2/3 ready
platform Deployment legacy-exporter: 1/2 ready
----
JSON
{
 "unhealthy": [
   {
     "namespace": "search-prod",
     "kind": "Deployment",
     "name": "search-api-canary",
     "desired": 1,
     "ready": 0,
     "unavailable": 1,
     "restarts": 0,
     "notReadyPods": [
       {
         "name": "search-api-canary-1122-zz99",
         "phase": "Pending",
         "reason": "ErrImagePull",
         "restartCount": 0
       }
     ]
   },
   {
     "namespace": "search-prod",
     "kind": "StatefulSet",
     "name": "search-index",
     "desired": 3,
     "ready": 2,
     "unavailable": 1,
     "restarts": 13,
     "notReadyPods": [
       {
         "name": "search-index-2",
         "phase": "Running",
         "reason": "CrashLoopBackOff",
         "restartCount": 12
       }
     ]
   },
   {
     "namespace": "platform",
     "kind": "Deployment",
     "name": "metrics-adapter",
     "desired": 3,
     "ready": 2,
     "unavailable": 1,
     "restarts": 47,
     "notReadyPods": [
       {
         "name": "metrics-adapter-9a1b-p2",
         "phase": "Pending",
         "reason": "ImagePullBackOff",
         "restartCount": 0
       }
     ]
   },
   {
     "namespace": "platform",
     "kind": "Deployment",
     "name": "legacy-exporter",
     "desired": 2,
     "ready": 1,
     "unavailable": 1,
     "restarts": 0,
     "notReadyPods": []
   }
 ]
}
```
## What was wrong

<!--
One line per defect: what it was, and what it would have done to us in production.
Include defects you found but chose not to fix, and say why.
-->

| # | Defect | Consequence | Fixed? |
| --- | --- | --- | --- |
| 1 | The original tool did not handle missing or invalid input files cleanly. | The tool could fail without giving the required exit code and error message, making monitoring or automation unable to distinguish a bad input from a healthy result. | Yes |
| 2 | A Deployment in a healthy RollingUpdate could be reported as unhealthy while replicas were temporarily being replaced. | A normal deployment could trigger a false alert during a rollout. | Yes |
| 3 | The StatefulSet test expected 0 ready replicas, while the sample data showed 2 ready replicas. | The test could report the wrong StatefulSet health. | Yes |
| 4 | Pod restart counts and failure reasons only considered regular container statuses, not init containers. | A failing init container could be missed when diagnosing an unhealthy Pod. | Yes |

## Decision log

<!--
The section we read most carefully. For each significant decision: what you chose, what
you rejected. Include the ones you're unsure about.
-->

| Decision | Chose | Rejected |
| --- | --- | --- |
| Replica health | Use the workload status fields (`readyReplicas` / `availableReplicas`) to calculate unavailable replicas. | Counting Pods manually as the primary source, because the workload status is the Kubernetes controller's view of replica availability. |
| Pod ownership | Follow Pod ownerReferences through ReplicaSet to the Deployment. | Matching Pods only by name or labels, because ownerReferences give a more reliable relationship. |
| Rolling updates | Ignore a Deployment with `RollingUpdate` strategy when both `Progressing=True` and `Available=True`. | Alerting only because `readyReplicas < desired`, because this would page during a normal rollout. |
| Pod failure reason | Use the waiting container reason when available, otherwise report `Unknown`. | Guessing a reason from the Pod phase or Pod name. |
| Input errors | Return exit code 2 and write the error to stderr. | Treating invalid input as an unhealthy workload, because an input problem is different from a cluster health problem. |

## Rolling updates vs. real outages

A Deployment can temporarily have fewer ready replicas during a normal RollingUpdate.

I chose not to alert when:
- the Deployment uses the RollingUpdate strategy
- Progressing=True
- Available=True

This avoids alerting on a normal rollout while the new Pods are replacing the old ones.
This is not a perfect guarantee. The supplied export is only a snapshot, so it cannot prove that a rollout will recover within 5 minutes. To make the 5-minute requirement reliable, I would need repeated observations over time, or Kubernetes events/metrics showing how long the workload has been degraded.
For a real production alert, I would keep the current snapshot check as one signal and add a time-based condition such as "unavailable replicas remain above zero for 5 minutes".

## Assumptions and limitations

- The input is a snapshot of the cluster, not a continuous stream of observations.
- A workload with replicas below the desired count is considered degraded unless it is a healthy RollingUpdate.
- Pod ownership is determined using ownerReferences. Pods whose ownership cannot be resolved are not attributed to a workload.
- The tool reports the best failure reason available from container status. If no reason is available, it reports Unknown.
- Restart counts are based on the container restartCount values available in the export.
- A snapshot cannot prove that a workload will recover within 5 minutes. A production implementation would need repeated observations or metrics.
- Jobs are inspected using their replica information, but completed Job Pods are not treated as unhealthy Pods.
- The tool is read-only and only processes the supplied JSON export.

## Productionising

I would first run the reporter as a read-only monitoring job against regular cluster exports.
Before allowing it to page a human, I would:
- Run it periodically and keep the last few results so short-lived problems do not immediately page.
- Alert only when a workload remains degraded for at least 5 minutes.
- Give the monitoring job read-only Kubernetes permissions if it reads the cluster directly.
- Keep the JSON output for monitoring systems and the human-readable output for on-call investigation.
- Include the namespace, workload, unavailable replicas, Pod reason and restart count in the alert.
- Monitor for flapping workloads so repeated short failures do not create excessive alerts.
For CI, I would use the same tool against exported cluster data and fail the check when a genuinely unhealthy workload is found.
I would also add more tests using real cluster edge cases before using the tool for production paging.

## AI usage and verification

**What I used AI for:**

- I used AI to review the existing code and suggest possible edge cases.
- I used it to help with small implementation and test changes.
- I treated the suggestions as a second opinion and verified them locally.

**What it got wrong:**

- The initial implementation did not handle some of the CLI requirements correctly.
- The test expectations for the StatefulSet did not match the actual sample data. Running the tool and the tests helped identify this.

**How I verified the parts that were right:**

- Ran the tool against `sample_cluster.json`.
- Checked the reported workloads, Pod reasons and restart counts.
- Ran the full pytest suite after the changes.
- Verified both normal and JSON output.
- Verified the behavior for healthy input and invalid input.
- Added a test for a healthy RollingUpdate.

**Transcript:** Summary of the AI-assisted review and debugging process. All implementation changes were verified locally using the supplied sample data and test suite.

## What I'd do with more time

- Add more tests for DaemonSets and Jobs, including edge cases around completed and failed Jobs.
- Handle more Kubernetes failure states, such as terminated containers and Pods stuck waiting for a long time.
- Improve Pod ownership handling for more controller types.
- Add a small integration test using a few more realistic cluster snapshots.
- Add clearer CLI help and validation for the input JSON structure.
- If this were used in production, connect the output to a monitoring system instead of relying only on a command-line run.
