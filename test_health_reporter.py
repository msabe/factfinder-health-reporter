"""Tests for health_reporter.

Run with:  python3 -m pytest tests/ -v

These tests were written alongside the current implementation and all pass.
"""

import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import health_reporter as hr  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
SAMPLE = REPO / "sample_cluster.json"
TOOL = REPO / "health_reporter.py"


@pytest.fixture(scope="module")
def sample_items():
    with open(SAMPLE, encoding="utf-8") as handle:
        return json.load(handle)["items"]


def find(reports, namespace, name):
    for report in reports:
        if report.namespace == namespace and report.name == name:
            return report
    return None


def pod(name, namespace="default", labels=None, phase="Running", containers=None):
    """Build a minimal Pod object."""
    return {
        "kind": "Pod",
        "metadata": {
            "namespace": namespace,
            "name": name,
            "labels": labels if labels is not None else {},
        },
        "status": {
            "phase": phase,
            "containerStatuses": containers if containers is not None else [],
        },
    }


def deployment(name, replicas, available, namespace="default", app=None):
    """Build a minimal Deployment object."""
    return {
        "kind": "Deployment",
        "metadata": {"namespace": namespace, "name": name},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": app or name}},
        },
        "status": {"availableReplicas": available},
    }


# --- replica accounting ------------------------------------------------------


def test_scaled_to_zero_is_not_reported():
    items = [deployment("batch-worker", replicas=0, available=0)]
    assert hr.build_report(items) == []


def test_fully_available_workload_is_not_reported():
    items = [deployment("metrics-adapter", replicas=2, available=2)]
    assert hr.build_report(items) == []


def test_under_replicated_workload_is_reported():
    items = [deployment("search-api", replicas=3, available=1)]
    reports = hr.build_report(items)
    assert len(reports) == 1
    assert reports[0].desired == 3
    assert reports[0].ready == 1
    assert reports[0].unavailable == 2


def test_statefulset_unavailable_replicas(sample_items):
    """search-index has 3 desired replicas and is missing all of them."""
    reports = hr.build_report(sample_items)
    sts = find(reports, "search-prod", "search-index")
    assert sts is not None
    assert sts.kind == "StatefulSet"
    assert sts.desired == 3
    assert sts.ready == 0
    assert sts.unavailable == 3


# --- pod readiness ----------------------------------------------------------


def test_pod_with_all_containers_ready_is_ready():
    assert hr.is_pod_ready(pod("p", containers=[{"name": "c", "ready": True}]))


def test_pod_with_unready_container_is_not_ready():
    assert not hr.is_pod_ready(pod("p", containers=[{"name": "c", "ready": False}]))


def test_pod_without_container_statuses_is_ready():
    """A Pod with no containerStatuses has nothing unready in it."""
    bare = {"kind": "Pod", "metadata": {"namespace": "default", "name": "p"}, "status": {"phase": "Pending"}}
    assert hr.is_pod_ready(bare) is True


def test_completed_job_pod_is_not_attributed_to_a_workload():
    items = [
        deployment("db-migration", replicas=1, available=0, app="db-migration"),
        pod(
            "db-migration-lm4z",
            labels={"app": "db-migration"},
            phase="Succeeded",
            containers=[{"name": "migrate", "ready": False}],
        ),
    ]
    reports = hr.build_report(items)
    assert len(reports) == 1
    assert reports[0].not_ready_pods == []


# --- reasons and restarts ---------------------------------------------------


def test_crashloop_reason_is_surfaced(sample_items):
    reports = hr.build_report(sample_items)
    sts = find(reports, "search-prod", "search-index")
    reasons = {p.reason for p in sts.not_ready_pods}
    assert "CrashLoopBackOff" in reasons


def test_restart_count_is_reported(sample_items):
    reports = hr.build_report(sample_items)
    sts = find(reports, "search-prod", "search-index")
    assert sts.restarts > 0


# --- CLI --------------------------------------------------------------------


def test_json_output_is_parseable():
    result = subprocess.run(
        [sys.executable, str(TOOL), str(SAMPLE), "--json"],
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert "unhealthy" in payload
    assert isinstance(payload["unhealthy"], list)


def test_missing_file_reports_an_error():
    result = subprocess.run(
        [sys.executable, str(TOOL), "/nonexistent/cluster.json"],
        capture_output=True,
        text=True,
    )
    assert "cannot inspect" in result.stderr


def test_healthy_input_exits_zero(tmp_path):
    path = tmp_path / "healthy.json"
    path.write_text(
        json.dumps({"kind": "List", "items": [deployment("ok", 2, 2)]}),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(TOOL), str(path)], capture_output=True, text=True
    )
    assert result.returncode == 0
