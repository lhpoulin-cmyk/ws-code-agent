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
| E9 | COVERED | `test_c01_restart_preserves_feedback_effect_and_validation`; `test_c02_restart_captures_exact_clarification_and_private_reference_only`; `test_six_case_registry_progresses_across_controller_restarts`; `test_c05_only_family_registration_and_progression` |
| H5 | COVERED | `test_single_protocol_examples_equal_active_parser_contract`; `test_multi_protocol_examples_equal_active_parser_contract`; `test_backend_renders_only_the_harness_owned_protocol` |
| H6 | COVERED | `test_c05_feedback_makes_effect_replay_authority_and_terminal_state_explicit` proves repository-neutral C05 authority, accepted-effect retention, replay denial, and terminal semantics are model-visible. |
| P10 | COVERED | `test_manifest_binds_clean_source_explicit_scope_and_qualification`; `test_scope_second_repository_and_stale_source_fail_closed`; `test_candidate_review_and_operator_disposition_never_promote_source` prove the production lane is qualification-bound, single-repository, explicitly scoped, isolated, and operator-gated. |
| P11 | COVERED | `test_read_distinguishes_bounded_absence_non_regular_and_escape`; `test_search_distinguishes_missing_non_directory_and_escape_scope`; `test_missing_authorized_read_can_progress_to_isolated_candidate` prove ordinary absence inside granted scope is distinct from traversal or symlink escape and remains usable by the supervised lane. |
| P12 | COVERED | `test_probe_has_fixed_read_only_authority_and_no_promotion_surface`; `test_default_controller_and_production_lane_cannot_resolve_probe_protocol`; `test_production_protocol_is_unchanged_and_probe_is_not_registered` prove the counterbalanced anchoring probe cannot acquire production qualification, mutation, promotion, or registered production-protocol authority. |
| P13 | COVERED | `test_value_free_v2_has_same_schema_without_populated_examples`; `test_frozen_v1_render_hashes_remain_unchanged`; `test_value_free_v2_is_candidate_only_and_uses_fixed_synthetic_fixtures` prove the candidate production protocol describes structure and types without arbitrary concrete repository/task values, while frozen V1 remains unchanged and V2 cannot bypass its synthetic-only qualification boundary. |
| G3 | PARTIAL | 2026-08-10: C03/C05 have no approved behavioral validators or private oracles. Unregistered `containment_required` descriptors fail closed; Task 10E must record `technical_validation = NOT_RUN` unless a future evaluator-owned descriptor is approved. |

`ApplicationStatus.SUCCESS` / projected `ACCEPTED` means only isolated,
authority-bounded patch application. It does not mean correct, validated, task
complete, or behaviorally acceptable.
