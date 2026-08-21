#!/usr/bin/env python3
"""Advisory check for nexlayer.yaml, run from a file-edit hook.

Why this exists: the server-side `nexlayer_validate_yaml` returns VALID for
several things the deployment contract calls hard constraints — an image with no
tag, an empty `servicePorts`, no pod exposing `path`, an invalid pod name, and
unknown fields. Those surface as a failed deploy minutes later instead. This
catches them at the moment the file is written. See docs/VALIDATION.md.

Contract with the host:
  * hook payload arrives as JSON on stdin (shape differs per host) or paths in argv
  * findings go to stdout, which hosts surface back to the agent
  * exit code is always 0 — this is advice, never a block

Run standalone too: hooks/nexlayer-yaml-check.py path/to/nexlayer.yaml
"""

from __future__ import annotations

import json
import os
import re
import select
import sys

APP_NAME = re.compile(r"^[a-z][a-z0-9.-]{2,63}$")
POD_NAME = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
VOLUME_SIZE = re.compile(r"^[0-9]+(Mi|Gi)$")
BROWSER_VAR = re.compile(r"^(NEXT_PUBLIC_|VITE_|REACT_APP_|PUBLIC_|VUE_APP_|EXPO_PUBLIC_)")
TARGET = re.compile(r"^nexlayer\.ya?ml$")

# Fields the platform documents. Anything else is silently ignored at deploy time,
# so flagging it here is the only signal a user gets.
APP_KEYS = {"version", "name", "url", "registryLogin", "pods"}
POD_KEYS = {
    "name", "image", "path", "servicePorts", "vars", "secrets", "volumes",
    "command", "args", "entrypoint", "resourceType", "replicas", "resources",
    "subdomain", "useGPU", "annotations",
}
V2_ONLY = ("resources", "resourceType", "replicas", "subdomain")


def candidate_paths(payload, out):
    """Collect anything in the hook payload that looks like a nexlayer.yaml path."""
    if isinstance(payload, dict):
        for value in payload.values():
            candidate_paths(value, out)
    elif isinstance(payload, list):
        for value in payload:
            candidate_paths(value, out)
    elif isinstance(payload, str):
        if TARGET.match(os.path.basename(payload)) and os.path.isfile(payload):
            out.append(payload)
    return out


def check(path):
    """Return a list of finding strings for one nexlayer.yaml."""
    findings = []
    raw = open(path, encoding="utf-8", errors="replace").read()

    try:
        import yaml
    except ImportError:
        # Degraded mode: no parser available, so check only what regex can see.
        for match in re.finditer(r"^\s*image:\s*([^\s#]+)", raw, re.M):
            image = match.group(1).strip("\"'")
            if ":" not in image.rsplit("/", 1)[-1]:
                findings.append(f"image `{image}` has no tag — the platform requires an explicit immutable tag")
            elif image.endswith(":latest"):
                findings.append(f"image `{image}` uses `latest`, which is rejected")
        if re.search(r"(NEXT_PUBLIC_|VITE_|REACT_APP_)[A-Z0-9_]*:\s*\S*\.pod", raw):
            findings.append("a browser-facing var points at `.pod` DNS — browsers cannot resolve it, use `<% URL %>`")
        return findings

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return [f"not parseable as YAML: {str(exc).splitlines()[0]}"]
    if not isinstance(doc, dict) or "application" not in doc:
        return ["no top-level `application:` key — this is not a Nexlayer deployment file"]

    app = doc.get("application") or {}
    if not isinstance(app, dict):
        return ["`application:` is not a mapping"]

    for key in sorted(set(app) - APP_KEYS):
        findings.append(f"application.{key} is not a documented field — the platform will ignore it")

    name = app.get("name")
    if not name:
        findings.append("application.name is missing")
    elif not APP_NAME.match(str(name)):
        findings.append(f"application.name `{name}` breaks `^[a-z][a-z0-9.-]{{2,63}}$`")

    v2 = str(app.get("version", "")) == "2.0"
    pods = app.get("pods") or []
    if not isinstance(pods, list) or not pods:
        findings.append("application.pods is empty — nothing would be deployed")
        return findings

    exposed = []
    for index, pod in enumerate(pods):
        if not isinstance(pod, dict):
            findings.append(f"pods[{index}] is not a mapping")
            continue
        label = pod.get("name") or f"pods[{index}]"

        for key in sorted(set(pod) - POD_KEYS):
            findings.append(f"pod `{label}`: `{key}` is not a documented field — the platform will ignore it")

        if not pod.get("name"):
            findings.append(f"pods[{index}]: missing `name`")
        elif not POD_NAME.match(str(pod["name"])):
            findings.append(
                f"pod `{label}`: name breaks `^[a-z][a-z0-9-]{{1,63}}$` — pod names become DNS labels, "
                "so this passes validation and then fails at deploy"
            )

        image = str(pod.get("image", ""))
        if not image:
            findings.append(f"pod `{label}`: missing `image`")
        elif ":" not in image.rsplit("/", 1)[-1]:
            findings.append(f"pod `{label}`: image `{image}` has no tag — an explicit immutable tag is required")
        elif image.endswith(":latest"):
            findings.append(f"pod `{label}`: image tag `latest` is rejected — use a version or git SHA")

        ports = pod.get("servicePorts")
        if pod.get("resourceType") != "job" and not ports:
            findings.append(f"pod `{label}`: `servicePorts` is missing or empty — routing and health checks need it")

        if pod.get("path"):
            exposed.append(label)

        if not v2:
            for key in V2_ONLY:
                if key in pod:
                    findings.append(
                        f"pod `{label}`: `{key}` needs `application.version: 2.0` — without it the platform "
                        "silently ignores the field and applies v1 behavior"
                    )
        if pod.get("subdomain") and not app.get("url"):
            findings.append(f"pod `{label}`: `subdomain` requires `application.url` (a custom domain)")

        for key, value in (pod.get("vars") or {}).items():
            text = str(value)
            if BROWSER_VAR.match(key) and ".pod" in text:
                findings.append(
                    f"pod `{label}`: `{key}` points at `.pod` DNS — a browser cannot resolve it, use `<% URL %>`"
                )
            if "localhost" in text or "127.0.0.1" in text:
                findings.append(f"pod `{label}`: `{key}` contains a loopback address, which never resolves in a container")

        for volume in pod.get("volumes") or []:
            if not isinstance(volume, dict):
                continue
            size = str(volume.get("size", ""))
            if size and not VOLUME_SIZE.match(size):
                findings.append(f"pod `{label}`: volume size `{size}` must look like `10Gi` or `512Mi`")
            mount = str(volume.get("mountPath", ""))
            if "postgres" in image and mount.rstrip("/").endswith("/data"):
                pgdata = str((pod.get("vars") or {}).get("PGDATA", ""))
                if not pgdata.startswith(mount.rstrip("/") + "/"):
                    findings.append(
                        f"pod `{label}`: volume mounts `{mount}` without `PGDATA` in a subdirectory — "
                        "initdb fails on the lost+found the platform creates there"
                    )

    if not exposed:
        findings.append("no pod defines `path` — nothing would be reachable from the internet")

    return findings


def read_payload(timeout=0.5):
    """Read the hook payload without ever hanging.

    Hosts pipe JSON and close stdin; a terminal or a host that leaves stdin open
    would otherwise block this script forever, so poll before reading.
    """
    if sys.stdin.isatty():
        return ""
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
    except (OSError, ValueError):
        return ""
    if not ready:
        return ""
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def main():
    # Explicit paths win, and mean stdin is irrelevant.
    raw = "" if len(sys.argv) > 1 else read_payload()

    paths = []
    if raw.strip():
        try:
            candidate_paths(json.loads(raw), paths)
        except (ValueError, TypeError):
            candidate_paths(raw, paths)
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            paths.append(arg)

    seen, unique = set(), []
    for path in paths:
        real = os.path.realpath(path)
        if real not in seen:
            seen.add(real)
            unique.append(path)

    for path in unique:
        try:
            findings = check(path)
        except Exception as exc:  # never break the caller's session over a check
            print(f"nexlayer.yaml check skipped for {path}: {exc}")
            continue
        if findings:
            print(f"nexlayer.yaml check — {len(findings)} issue(s) in {path}:")
            for finding in findings:
                print(f"  - {finding}")
            print("These are not all caught by nexlayer_validate_yaml; fix them before deploying.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
