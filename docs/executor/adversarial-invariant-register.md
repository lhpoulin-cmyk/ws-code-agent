# Adversarial Invariant Register — Alpha gate v1

Last reviewed: 2026-08-10. This register is executable memory: every
`COVERED` row names a focused test. `PARTIAL` rows contain a dated, bounded
Task 10E triage. No row is `MISSING`.

| ID | Status | Enforcement test / triage |
| --- | --- | --- |
| P3 | COVERED | `test_dangling_symlink_and_git_metadata_targets_are_denied` |
| P5 | COVERED | `test_success_isolated_and_authoritative_source_is_unchanged` |
| P6 | COVERED | `test_ambiguous_cleanup_and_reconstruction_mismatch_fail_closed` |
| S2 | COVERED | `test_scope_traversal_absolute_and_multi_file_denials_leave_copy_unchanged` |
| S3 | COVERED | `test_header_target_mismatch_scope_and_repository_binding_are_denied` |
| S4 | COVERED | `test_dangling_symlink_and_git_metadata_targets_are_denied` |
| V1 | COVERED | `test_header_target_mismatch_scope_and_repository_binding_are_denied` |
| V2 | COVERED | `test_pass_fail_streams_unknown_and_wrong_snapshot` |
| V6 | COVERED | stale-bound read/search tests in `test_readonly_executor.py` |
| T1 | COVERED | `test_ambiguous_cleanup_and_reconstruction_mismatch_fail_closed` |
| T4 | COVERED | `test_repository_replacement_at_same_path_changes_identity` |
| X3 | COVERED | `test_containment_required_unregistered_case_fails_closed_and_descriptors_reject_shell` |
| X4 | COVERED | same test; descriptor-only executor fixes executable/argv/env and rejects shell syntax |
| M3 | COVERED | `test_aggregate_uses_required_change_set_and_never_claims_correctness` |
| M4 | COVERED | `test_aggregate_uses_required_change_set_and_never_claims_correctness` |
| R1 | COVERED | `test_active_tracked_tree_excludes_inherited_doc_writer_runtime_identity` |
| E6 | COVERED | `test_raw_response_is_durable_before_recovery_and_never_regenerated`; `test_durable_sink_precedes_disposable_cleanup_and_failure_retains_output` |
| E7 | COVERED | restart adapter tests in `test_alpha_case_adapters.py`, including workspace tamper denial before inference |
| E8 | COVERED | `test_intent_survives_remote_success_disconnect_and_recovers_once`; gpu-compute `tests/unit/idempotent-run.sh` covers duplicate, concurrent, mismatch, and terminal failure replay |
| H5 | COVERED | `test_single_protocol_examples_equal_active_parser_contract`; `test_multi_protocol_examples_equal_active_parser_contract`; `test_backend_renders_only_the_harness_owned_protocol` |
| G3 | PARTIAL | 2026-08-10: C03/C05 have no approved behavioral validators or private oracles. Unregistered `containment_required` descriptors fail closed; Task 10E must record `technical_validation = NOT_RUN` unless a future evaluator-owned descriptor is approved. |

`ApplicationStatus.SUCCESS` / projected `ACCEPTED` means only isolated,
authority-bounded patch application. It does not mean correct, validated, task
complete, or behaviorally acceptable.
