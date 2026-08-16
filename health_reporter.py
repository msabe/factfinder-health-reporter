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
   container_statuses = pod.get("status", {}).get("containerStatuses", [])
   restart_count = sum(
       container.get("restartCount", 0)
       for container in container_statuses
   )
   reason = "Unknown"
   for container in container_statuses:
       state = container.get("state", {})
       if state.get("waiting", {}).get("reason"):
           reason = state["waiting"]["reason"]
           break
   return {
       "name": pod.get("metadata", {}).get("name", "Unknown"),
       "phase": pod.get("status", {}).get("phase", "Unknown"),
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