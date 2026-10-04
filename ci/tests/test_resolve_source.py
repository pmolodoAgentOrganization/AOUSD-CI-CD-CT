"""Test BuildUSD source event validation."""

import unittest

from ci.resolve_source import resolve_source


EXPECTED_SOURCE_REPOSITORY = "source-owner/openusd-source"
SOURCE_SHA = "1" * 40


def dispatch(source_event_name, source_ref, **inputs):
    return {
        "inputs": {
            "source_event_name": source_event_name,
            "source_ref": source_ref,
            "source_repository": EXPECTED_SOURCE_REPOSITORY,
            "source_sha": SOURCE_SHA,
            **inputs,
        },
    }


class ResolveSourceTest(unittest.TestCase):
    def test_local_events_use_the_pinned_submodule(self):
        for event_name in ("pull_request", "push"):
            with self.subTest(event_name=event_name):
                result = resolve_source(event_name, {})
                self.assertEqual(result["checkout-submodules"], "recursive")
                self.assertEqual(result["external-source"], "false")
                self.assertEqual(result["source-event-name"], event_name)
                self.assertEqual(result["source-repository"], "")

    def test_dev_push_is_accepted(self):
        event = dispatch("push", "refs/heads/dev")
        result = resolve_source(
            "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
        )
        self.assertEqual(result["checkout-submodules"], "false")
        self.assertEqual(result["external-source"], "true")
        self.assertEqual(result["source-repository"], EXPECTED_SOURCE_REPOSITORY)
        self.assertEqual(result["source-sha"], SOURCE_SHA)

    def test_build_ig_push_is_accepted(self):
        event = dispatch("push", "refs/heads/build-ig")
        result = resolve_source(
            "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
        )
        self.assertEqual(result["source-ref"], "refs/heads/build-ig")

    def test_version_tag_push_is_accepted(self):
        event = dispatch("push", "refs/tags/v26.11")
        result = resolve_source(
            "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
        )
        self.assertEqual(result["source-ref"], "refs/tags/v26.11")

    def test_pull_request_merge_is_accepted(self):
        event = dispatch(
            "pull_request",
            "refs/pull/123/merge",
            pull_request="123",
            source_base_ref="dev",
        )
        result = resolve_source(
            "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
        )
        self.assertEqual(result["source-event-name"], "pull_request")

    def test_unexpected_repository_is_rejected(self):
        event = dispatch("push", "refs/heads/dev")
        event["inputs"]["source_repository"] = "example/OpenUSD"
        with self.assertRaisesRegex(ValueError, "Expected source repository"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)

    def test_unexpected_push_ref_is_rejected(self):
        event = dispatch("push", "refs/heads/feature")
        with self.assertRaisesRegex(ValueError, "allowed source branch"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)

    def test_build_ig_pull_request_is_accepted(self):
        event = dispatch(
            "pull_request",
            "refs/pull/123/merge",
            pull_request="123",
            source_base_ref="build-ig",
        )
        result = resolve_source(
            "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
        )
        self.assertEqual(result["source-ref"], "refs/pull/123/merge")

    def test_unexpected_pull_request_base_is_rejected(self):
        event = dispatch(
            "pull_request",
            "refs/pull/123/merge",
            pull_request="123",
            source_base_ref="release",
        )
        with self.assertRaisesRegex(ValueError, "allowed source branch"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)

    def test_invalid_pull_request_number_is_rejected(self):
        for pull_request in (
            None, "", "not-a-number", "0", "-1", "1.5", "1e2", " 123",
            "0123", True, 0, 123, 1.5,
        ):
            with self.subTest(pull_request=pull_request):
                event = dispatch(
                    "pull_request",
                    "refs/pull/123/merge",
                    pull_request=pull_request,
                    source_base_ref="dev",
                )
                with self.assertRaisesRegex(ValueError, "positive pull_request"):
                    resolve_source(
                        "workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY
                    )

    def test_mismatched_pull_request_ref_is_rejected(self):
        event = dispatch(
            "pull_request",
            "refs/pull/124/merge",
            pull_request="123",
            source_base_ref="dev",
        )
        with self.assertRaisesRegex(ValueError, "Expected pull request source ref"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)

    def test_invalid_sha_is_rejected(self):
        event = dispatch("push", "refs/heads/dev")
        event["inputs"]["source_sha"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "Invalid source SHA"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)

    def test_missing_source_repository_configuration_is_rejected(self):
        event = dispatch("push", "refs/heads/dev")
        with self.assertRaisesRegex(ValueError, "must be configured"):
            resolve_source("workflow_dispatch", event)

    def test_unexpected_source_event_is_rejected(self):
        event = dispatch("release", "refs/heads/dev")
        with self.assertRaisesRegex(ValueError, "Unsupported source event"):
            resolve_source("workflow_dispatch", event, EXPECTED_SOURCE_REPOSITORY)


if __name__ == "__main__":
    unittest.main()
