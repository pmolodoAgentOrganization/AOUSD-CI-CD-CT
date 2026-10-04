#!/usr/bin/env python

"""Validate a BuildUSD trigger and emit the source checkout configuration."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import traceback


SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
SOURCE_BRANCHES = {"build-ig", "dev"}
SOURCE_BRANCH_REFS = {f"refs/heads/{branch}" for branch in SOURCE_BRANCHES}
VERSION_TAG_PATTERN = re.compile(r"refs/tags/v[0-9]{2}\.[0-9]{2}")


def _required_string(mapping, key):
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Workflow dispatch input {key!r} must be a non-empty string"
        )
    return value


def _resolve_source(event_name, event, expected_source_repository=None):
    if event_name in {"pull_request", "push"}:
        return {
            "source-event-name": event_name,
            "source-ref": "",
            "source-repository": "",
            "source-sha": "",
        }
    if event_name != "workflow_dispatch":
        raise ValueError(f"Unsupported workflow event: {event_name}")
    if not expected_source_repository:
        raise ValueError("The OpenUSD Source repository must be configured")

    inputs = event.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("Workflow dispatch inputs must be an object")

    repository = _required_string(inputs, "source_repository")
    source_event_name = _required_string(inputs, "source_event_name")
    source_ref = _required_string(inputs, "source_ref")
    source_sha = _required_string(inputs, "source_sha")

    if repository != expected_source_repository:
        raise ValueError(
            f"Expected source repository {expected_source_repository}, got {repository}"
        )
    if not SHA_PATTERN.fullmatch(source_sha):
        raise ValueError(f"Invalid source SHA: {source_sha}")

    if source_event_name == "push":
        if source_ref not in SOURCE_BRANCH_REFS and not VERSION_TAG_PATTERN.fullmatch(
            source_ref
        ):
            raise ValueError(
                "Push dispatch does not target an allowed source branch or a "
                f"version tag: {source_ref}"
            )
    elif source_event_name == "pull_request":
        pull_request = inputs.get("pull_request")
        if (
            not isinstance(pull_request, str)
            or not re.fullmatch(r"[1-9][0-9]*", pull_request)
        ):
            raise ValueError("Pull request dispatch must include a positive pull_request")
        source_base_ref = _required_string(inputs, "source_base_ref")
        if source_base_ref not in SOURCE_BRANCHES:
            raise ValueError(
                "Pull request dispatch does not target an allowed source branch: "
                f"{source_base_ref}"
            )
        expected_ref = f"refs/pull/{pull_request}/merge"
        if source_ref != expected_ref:
            raise ValueError(
                f"Expected pull request source ref {expected_ref}, got {source_ref}"
            )
    else:
        raise ValueError(f"Unsupported source event: {source_event_name}")

    return {
        "source-event-name": source_event_name,
        "source-ref": source_ref,
        "source-repository": repository,
        "source-sha": source_sha,
    }


def resolve_source(event_name, event, expected_source_repository=None):
    outputs = _resolve_source(event_name, event, expected_source_repository)
    external_source = bool(outputs["source-repository"])
    outputs["checkout-submodules"] = "false" if external_source else "recursive"
    outputs["external-source"] = "true" if external_source else "false"
    return outputs


def write_outputs(outputs, output_path):
    with output_path.open("a", encoding="utf-8") as output_file:
        for key, value in outputs.items():
            print(f"{key}={value}", file=output_file)


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--expected-source-repository",
        default=os.environ.get("OPENUSD_SOURCE_REPOSITORY"),
        help="Allowed OWNER/REPO for external OpenUSD Source events",
    )
    parser.add_argument(
        "--event-name",
        default=os.environ.get("GITHUB_EVENT_NAME"),
        help="GitHub Actions event name",
    )
    parser.add_argument(
        "--event-path",
        type=Path,
        default=os.environ.get("GITHUB_EVENT_PATH"),
        help="Path to the GitHub event JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=os.environ.get("GITHUB_OUTPUT"),
        help="Path to the GitHub Actions output file",
    )
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = get_parser().parse_args(argv)
    try:
        if not args.event_name:
            raise ValueError("An event name is required")
        if args.event_path is None:
            raise ValueError("An event JSON path is required")
        if args.output is None:
            raise ValueError("An output path is required")
        with args.event_path.open(encoding="utf-8") as event_file:
            event = json.load(event_file)
        write_outputs(
            resolve_source(
                args.event_name,
                event,
                expected_source_repository=args.expected_source_repository,
            ),
            args.output,
        )
    except Exception:  # pylint: disable=broad-except
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
