#!/usr/bin/env python3
"""
StegVerse Org Discovery Tool

Examines a GitHub org for StegVerse ecosystem components,
produces a delta report for bootstrap decisions.

Usage:
    python discover.py --org StegVerse-Labs --tier full
    python discover.py --org StegVerse-org --tier standard
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
import subprocess


def run_gh_api(endpoint: str) -> Optional[dict]:
    """Call GitHub CLI API."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def get_repos(org: str) -> List[str]:
    """List all repos in org."""
    data = run_gh_api(f"/orgs/{org}/repos?per_page=100")
    if not data:
        return []
    return [r["name"] for r in data]


def get_repo_contents(org: str, repo: str, path: str = "") -> List[dict]:
    """List contents of a repo path."""
    return run_gh_api(f"/repos/{org}/{repo}/contents/{path}") or []


def get_workflow_runs(org: str, repo: str, workflow: str) -> List[dict]:
    """Get recent workflow runs."""
    data = run_gh_api(f"/repos/{org}/{repo}/actions/workflows/{workflow}/runs?per_page=5")
    if not data:
        return []
    return data.get("workflow_runs", [])


def get_latest_commit(org: str, repo: str, path: str = "") -> Optional[str]:
    """Get date of latest commit to a path."""
    data = run_gh_api(f"/repos/{org}/{repo}/commits?path={path}&per_page=1")
    if not data or not isinstance(data, list):
        return None
    return data[0].get("commit", {}).get("committer", {}).get("date")


def check_file_exists(org: str, repo: str, path: str) -> bool:
    """Check if a specific file exists in repo."""
    result = run_gh_api(f"/repos/{org}/{repo}/contents/{path}")
    return result is not None


def check_secret_exists(org: str, secret_name: str) -> bool:
    """Check if a repository secret exists (checks current repo)."""
    # Note: This checks the current repo's secrets, not org-level
    # For org-level, use /orgs/{org}/secrets/{secret_name}
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{org}/{org}/actions/secrets/{secret_name}"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False


def discover_component(org: str, repo: str, component: str, tier: str) -> dict:
    """Discover state of a single component."""

    component_checks = {
        "ingest_lite": {
            "files": [".github/workflows/ingest-bundle.yml", "ingest/README.md"],
            "workflows": ["ingest-bundle.yml"]
        },
        "cge_lite": {
            "files": [".github/workflows/cge-validate.yml", "cge/policy.json"],
            "workflows": ["cge-validate.yml"]
        },
        "stegdb_lite": {
            "files": ["stegdb/config.json", ".github/workflows/stegdb-sync.yml"],
            "workflows": ["stegdb-sync.yml"]
        },
        "tv_tvc": {
            "files": ["tv/config.json", "tvc/config.json"],
            "workflows": []
        },
        "sandbox_runner": {
            "files": [
                "runner/main.py",
                "scripts/reconstruct.py",
                "scripts/replay.py",
                "scripts/governance_matrix.py",
                "scripts/governance_random_sweep.py"
            ],
            "workflows": ["run-demo.yml"]
        },
        "policy_engine": {
            "files": ["policy/baseline.json", ".github/workflows/policy-check.yml"],
            "workflows": ["policy-check.yml"]
        },
        "drift_checks": {
            "files": [".github/workflows/drift-check.yml"],
            "workflows": ["drift-check.yml"]
        },
        "dependency_tracker": {
            "files": ["deps/manifest.json"],
            "workflows": []
        },
        "ledger": {
            "files": ["ledger/config.json", ".github/workflows/ledger-sync.yml"],
            "workflows": ["ledger-sync.yml"]
        },
        "diagnostics": {
            "files": [".github/workflows/bootstrap-diagnostics.yml"],
            "workflows": ["bootstrap-diagnostics.yml"]
        }
    }

    checks = component_checks.get(component, {"files": [], "workflows": []})

    # Check files
    found_files = []
    missing_files = []
    for f in checks["files"]:
        if check_file_exists(org, repo, f):
            found_files.append(f)
        else:
            missing_files.append(f)

    # Check workflows
    workflow_status = []
    for wf in checks["workflows"]:
        runs = get_workflow_runs(org, repo, wf)
        if runs:
            latest = runs[0]
            workflow_status.append({
                "workflow": wf,
                "last_run": latest.get("created_at"),
                "status": latest.get("conclusion", "unknown"),
                "run_id": latest.get("id")
            })

    # Determine status
    if not checks["files"] and not checks["workflows"]:
        status = "not_started"
    elif missing_files and found_files:
        status = "partial"
    elif found_files and not missing_files:
        status = "installed"
    else:
        status = "missing"

    # Get latest commit date for component files
    latest_commit = None
    if found_files:
        latest_commit = get_latest_commit(org, repo, found_files[0])

    return {
        "status": status,
        "found_files": found_files,
        "missing_files": missing_files,
        "workflow_status": workflow_status,
        "latest_commit": latest_commit
    }


def discover_stegdb_state(org: str) -> dict:
    """Check StegDB registration and state."""
    # Try to read stegdb.config.json from any repo
    repos = get_repos(org)
    stegdb_state = {"registered": False, "tier": "unknown", "last_sync": None}

    for repo in repos:
        if check_file_exists(org, repo, "stegdb/config.json"):
            # Try to read the config
            try:
                result = subprocess.run(
                    ["gh", "api", f"/repos/{org}/{repo}/contents/stegdb/config.json"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    content = data.get("content", "")
                    if content:
                        import base64
                        config = json.loads(base64.b64decode(content).decode())
                        stegdb_state = {
                            "registered": True,
                            "tier": config.get("tier", "unknown"),
                            "last_sync": config.get("last_sync"),
                            "repo": repo
                        }
                        break
            except:
                pass

    return stegdb_state


def generate_report(org: str, target_tier: str, repos: List[str]) -> dict:
    """Generate full discovery report."""

    # Map components to expected repos
    component_repo_map = {
        "ingest_lite": "ingest-lite",
        "cge_lite": "cge-lite",
        "stegdb_lite": "StegDB",
        "tv_tvc": "TV",
        "sandbox_runner": "demo-suite-runner",
        "policy_engine": "policy-engine",
        "drift_checks": "drift-check",
        "dependency_tracker": "StegDB",
        "ledger": "StegDB",
        "diagnostics": "bootstrap"
    }

    components = {}
    for component, expected_repo in component_repo_map.items():
        # Find the actual repo (might be named differently)
        actual_repo = None
        for repo in repos:
            if expected_repo.lower() in repo.lower():
                actual_repo = repo
                break

        if actual_repo:
            components[component] = discover_component(org, actual_repo, component, target_tier)
            components[component]["repo"] = actual_repo
        else:
            components[component] = {
                "status": "missing",
                "repo": None,
                "found_files": [],
                "missing_files": [],
                "workflow_status": [],
                "latest_commit": None
            }

    # Determine detected tier
    installed_count = sum(1 for c in components.values() if c["status"] == "installed")
    partial_count = sum(1 for c in components.values() if c["status"] == "partial")

    if installed_count >= 8:
        detected_tier = "full"
    elif installed_count >= 4:
        detected_tier = "standard"
    elif installed_count >= 2:
        detected_tier = "core"
    else:
        detected_tier = "none"

    # Generate issues
    issues = []
    for comp, data in components.items():
        if data["status"] == "partial":
            issues.append({
                "severity": "warning",
                "component": comp,
                "message": f"Partial install — missing: {', '.join(data['missing_files'][:3])}"
            })
        elif data["status"] == "missing" and comp in get_required_components(target_tier):
            issues.append({
                "severity": "error",
                "component": comp,
                "message": f"Required for {target_tier} tier but not found"
            })

    # Determine overall status
    if all(c["status"] == "installed" for c in components.values()):
        overall_status = "complete"
    elif any(c["status"] == "partial" for c in components.values()):
        overall_status = "partial"
    elif any(c["status"] == "installed" for c in components.values()):
        overall_status = "in_progress"
    else:
        overall_status = "empty"

    stegdb_state = discover_stegdb_state(org)

    return {
        "org": org,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "target_tier": target_tier,
        "detected_tier": detected_tier,
        "overall_status": overall_status,
        "stegdb_state": stegdb_state,
        "components": components,
        "issues": issues,
        "repo_count": len(repos),
        "recommendation": generate_recommendation(components, target_tier, overall_status)
    }


def get_required_components(tier: str) -> List[str]:
    """Get required components for a tier."""
    tiers = {
        "core": ["ingest_lite", "cge_lite", "stegdb_lite"],
        "standard": ["ingest_lite", "cge_lite", "stegdb_lite", "tv_tvc", "sandbox_runner", "policy_engine"],
        "full": ["ingest_lite", "cge_lite", "stegdb_lite", "tv_tvc", "sandbox_runner", 
                 "policy_engine", "drift_checks", "dependency_tracker", "ledger", "diagnostics"]
    }
    return tiers.get(tier, tiers["core"])


def generate_recommendation(components: dict, target_tier: str, overall_status: str) -> str:
    """Generate human-readable recommendation."""
    if overall_status == "complete":
        return "All components installed. Run diagnostics to verify health."

    # Find first missing or partial component in required list
    required = get_required_components(target_tier)
    for comp in required:
        if components[comp]["status"] in ["missing", "partial", "not_started"]:
            if components[comp]["status"] == "partial":
                return f"Resume from {comp} — complete partial installation"
            else:
                return f"Start with {comp} — begin {target_tier} tier installation"

    return "Review optional components for upgrade"


def main():
    parser = argparse.ArgumentParser(description="StegVerse Org Discovery Tool")
    parser.add_argument("--org", required=True, help="GitHub org name")
    parser.add_argument("--tier", default="core", choices=["core", "standard", "full"],
                        help="Target tier to check against")
    parser.add_argument("--output", default="discovery_report.json", help="Output file")
    parser.add_argument("--format", default="json", choices=["json", "md"],
                        help="Output format")
    args = parser.parse_args()

    print(f"Discovering org: {args.org}")
    print(f"Target tier: {args.tier}")

    repos = get_repos(args.org)
    print(f"Found {len(repos)} repos")

    report = generate_report(args.org, args.tier, repos)

    # Write report
    if args.format == "json":
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
    else:
        write_markdown_report(report, args.output)

    print(f"\nDiscovery complete: {report['overall_status']}")
    print(f"Detected tier: {report['detected_tier']}")
    print(f"Target tier: {report['target_tier']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Report saved: {args.output}")

    # Exit code: 0 if complete, 1 if partial/missing
    if report['overall_status'] == 'complete':
        return 0
    return 1


def write_markdown_report(report: dict, filename: str):
    """Generate markdown report."""
    lines = [
        f"# StegVerse Discovery Report: {report['org']}",
        "",
        f"**Scan time:** {report['scan_time']}",
        f"**Overall status:** {report['overall_status']}",
        f"**Detected tier:** {report['detected_tier']}",
        f"**Target tier:** {report['target_tier']}",
        f"**Repos found:** {report['repo_count']}",
        "",
        "## StegDB State",
        "",
        f"- **Registered:** {report['stegdb_state']['registered']}",
        f"- **Tier:** {report['stegdb_state']['tier']}",
        f"- **Last sync:** {report['stegdb_state'].get('last_sync', 'never')}",
        "",
        "## Components",
        "",
        "| Component | Status | Repo | Files | Workflows | Last Commit |",
        "|-----------|--------|------|-------|-----------|-------------|",
    ]

    for comp, data in report['components'].items():
        files = f"{len(data['found_files'])}/{len(data['found_files']) + len(data['missing_files'])}"
        workflows = len(data['workflow_status'])
        commit = data.get('latest_commit', 'never')[:10] if data.get('latest_commit') else 'never'
        repo = data.get('repo', 'none') or 'none'
        lines.append(f"| {comp} | {data['status']} | {repo} | {files} | {workflows} | {commit} |")

    lines.extend([
        "",
        "## Issues",
        "",
    ])

    if report['issues']:
        for issue in report['issues']:
            emoji = "🔴" if issue['severity'] == 'error' else "🟡" if issue['severity'] == 'warning' else "🔵"
            lines.append(f"{emoji} **{issue['severity'].upper()}** — {issue['component']}: {issue['message']}")
    else:
        lines.append("No issues detected.")

    lines.extend([
        "",
        "## Recommendation",
        "",
        f"**{report['recommendation']}**",
        "",
    ])

    with open(filename, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    exit(main())
