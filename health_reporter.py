from dataclasses import dataclass

@dataclass
class WorkloadReport:
   namespace: str
   kind: str
   name: str
   desired: int
   ready: int
   unavailable: int
   not_ready_pods: list
   restarts: int

def is_pod_ready(pod):
   container_statuses = pod.get("status", {}).get("containerStatuses", [])
   for container in container_statuses:
       if not container.get("ready", False):
           return False
   return True

def get_pod_info(pod):
   status = pod.get("status", {})
   container_statuses = status.get("containerStatuses", [])
   init_statuses = status.get("initContainerStatuses", [])
   all_containers = init_statuses + container_statuses
   restart_count = sum(
       container.get("restartCount", 0)
       for container in all_containers
   )
   reason = "Unknown"
   for container in all_containers:
       state = container.get("state", {})
       if state.get("waiting", {}).get("reason"):
           reason = state["waiting"]["reason"]
           break
   return {
       "name": pod.get("metadata", {}).get("name", "Unknown"),
       "phase": status.get("phase", "Unknown"),
       "reason": reason,
       "restartCount": restart_count,
   }

def get_owner(pod):
   owners = pod.get("metadata", {}).get("ownerReferences", [])
   for owner in owners:
       if owner.get("controller"):
           return owner.get("kind"), owner.get("name")
   return None, None

def resolve_workload_owner(pod, replicasets):
   owner_kind, owner_name = get_owner(pod)
   if owner_kind != "ReplicaSet":
       return owner_kind, owner_name
   for replicaset in replicasets:
       metadata = replicaset.get("metadata", {})
       if metadata.get("name") != owner_name:
           continue
       rs_owner_kind, rs_owner_name = get_owner(replicaset)
       if rs_owner_kind == "Deployment":
           return rs_owner_kind, rs_owner_name
   return None, None

def get_workloads(items):
   workload_kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job"}
   return [
       item for item in items
       if item.get("kind") in workload_kinds
   ]

def get_replica_counts(workload):
   spec = workload.get("spec", {})
   status = workload.get("status", {})
   desired = spec.get("replicas", 0)
   ready = status.get("readyReplicas", status.get("availableReplicas", 0))
   unavailable = max(desired - ready, 0)
   return desired, ready, unavailable

def is_rolling_update(workload):
    if workload.get("kind") != "Deployment":
        return False
    strategy = workload.get("spec", {}).get("strategy", {})
    if strategy.get("type") != "RollingUpdate":
        return False
    conditions = workload.get("status", {}).get("conditions", [])
    progressing = False
    available = False
    for condition in conditions:
        if condition.get("type") == "Progressing":
            progressing = condition.get("status") == "True"
        if condition.get("type") == "Available":
            available = condition.get("status") == "True"
    return progressing and available

def build_report(items):
    replicasets = [
        item for item in items
        if item.get("kind") == "ReplicaSet"
    ]
    workloads = get_workloads(items)
    reports = []
    for workload in workloads:
        desired, ready, unavailable = get_replica_counts(workload)
        if desired == 0:
            continue
        namespace = workload.get("metadata", {}).get("namespace", "default")
        name = workload.get("metadata", {}).get("name", "")
        not_ready_pods = []
        restarts = 0
        for pod in items:
            if pod.get("kind") != "Pod":
                continue
            pod_namespace = pod.get("metadata", {}).get("namespace", "default")
            if pod_namespace != namespace:
                continue
            owner_kind, owner_name = resolve_workload_owner(
                pod, replicasets
            )
            if owner_kind != workload.get("kind"):
                continue
            if owner_name != name:
                continue
            pod_restarts = get_pod_info(pod)["restartCount"]
            restarts += pod_restarts
            if not is_pod_ready(pod):
                not_ready_pods.append(get_pod_info(pod))
        if unavailable > 0:
            if is_rolling_update(workload):
                continue
            reports.append(
                WorkloadReport(
                    namespace=namespace,
                    kind=workload.get("kind"),
                    name=name,
                    desired=desired,
                    ready=ready,
                    unavailable=unavailable,
                    not_ready_pods=not_ready_pods,
                    restarts=restarts,
                )
            )
    return reports

import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        with open(args.input_file, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot inspect input: {exc}", file=sys.stderr)
        return 2
    reports = build_report(data.get("items", []))
    if args.json:
        output = {
            "unhealthy": [
                {
                    "namespace": report.namespace,
                    "kind": report.kind,
                    "name": report.name,
                    "desired": report.desired,
                    "ready": report.ready,
                    "unavailable": report.unavailable,
                    "restarts": report.restarts,
                    "notReadyPods": report.not_ready_pods,
                }
                for report in reports
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        for report in reports:
            print(
                f"{report.namespace} {report.kind} {report.name}: "
                f"{report.ready}/{report.desired} ready"
            )
    return 1 if reports else 0

if __name__ == "__main__":
    sys.exit(main())
 
 