from docwriter_web.recovery_guidance import guidance_for
from test_web_app import app, request, trial_page


def trial(status="REVIEW_REQUIRED", **extra):
    value = {"trial_id": "trial-test", "review_status": status, "lifecycle_state": "ACTIVE", "source_state": "PRESENT", "integrity_findings": "[]", "normalized_output": "proposal", "project_slug": "alpha"}
    value.update(extra)
    return value


def attempt(status, error_class="", normalized="proposal"):
    return {"attempt_id": "attempt-test", "status": status, "error_class": error_class, "normalized_proposal": normalized, "prompt_version": "prompt-v1"}


def test_guidance_covers_resume_states_without_blame_language():
    cases = [
        (guidance_for(trial("REJECTED"), review_events=[]), "REVIEW_RATIONALE_MISSING"),
        (guidance_for(trial(), attempts=[]), "GENERATION_NOT_STARTED"),
        (guidance_for(trial(), [attempt("RUNNING")]), "GENERATION_RUNNING"),
        (guidance_for(trial(), [attempt("INTERRUPTED")]), "GENERATION_INTERRUPTED"),
        (guidance_for(trial(), [attempt("FAILED", "OLLAMA_UNAVAILABLE")]), "OLLAMA_UNAVAILABLE"),
        (guidance_for(trial(), [attempt("FAILED", "RESPONSE_SCHEMA_INVALID", "")]), "NO_NORMALIZED_PROPOSAL"),
        (guidance_for(trial(integrity_findings='[{"category":"ambiguity","detail":"structural"}]'), [attempt("COMPLETED")]), "INTEGRITY_REVIEW_REQUIRED"),
        (guidance_for(trial(), [attempt("COMPLETED")]), "REVISION_REVIEW_REQUIRED"),
        (guidance_for(trial("ACCEPTED"), [attempt("COMPLETED")]), "TONE_REVIEW_UNAVAILABLE"),
        (guidance_for(trial("ACCEPTED"), [attempt("COMPLETED")], tone_available=True), "AUDIENCE_WORK_UNAVAILABLE"),
        (guidance_for(trial(lifecycle_state="ARCHIVED"), [attempt("COMPLETED")]), "ARCHIVED_TRIAL"),
        (guidance_for(trial(lifecycle_state="ARCHIVED", source_state="OPERATOR_DELETED_TEST_CONTENT", recovery_state="PROVENANCE_ONLY"), [attempt("COMPLETED")]), "PROVENANCE_ONLY"),
        (guidance_for(trial(project_slug=None, project_id=None), [attempt("COMPLETED")]), "MISSING_PROJECT_CONTEXT"),
    ]
    forbidden = ("you forgot", "you failed", "you should have", "simply", "just")
    for guidance, expected in cases:
        assert guidance.guidance_id == expected
        assert guidance.title and guidance.explanation and guidance.preserved_work
        if guidance.primary_action_url:
            assert guidance.primary_action_url.startswith("/")
        text = " ".join((guidance.title, guidance.explanation, guidance.preserved_work, guidance.why_it_matters)).lower()
        assert not any(word in text for word in forbidden)


def test_unknown_state_fails_honestly_and_keeps_history_action():
    result = guidance_for(trial("UNSUPPORTED"), [attempt("COMPLETED")], audience_available=True, tone_available=True)
    assert result.guidance_id == "UNKNOWN_NEXT_STEP"
    assert result.title == "Doc Writer cannot determine the next step from the available record."
    assert result.primary_action_url.endswith("#generation-attempts")


def test_trial_and_queue_surfaces_explain_next_action_with_accessible_targets(tmp_path):
    application = app(tmp_path)
    created = request(application, "/trial", "POST", {"source_text": "A disposable validation source.", "model_identifier": "mistral-nemo:12b-instruct-2407-q4_K_M", "csrf": "x"})
    trial_id = created["headers"][0][1].rsplit("/", 1)[-1]
    page = trial_page(application, trial_id)["body"]
    assert "This trial has a saved source paragraph" in page
    assert f"/project/alpha/trial/{trial_id}#generation-attempts" in page
    assert "aria-labelledby='guidance-title'" in page
    queue = request(application, "/review-queue")["body"]
    assert "This trial has a saved source paragraph" in queue
    assert "Generate conversational proposal" in queue


def test_empty_review_queue_has_history_path(tmp_path):
    application = app(tmp_path)
    with application._db() as db:
        db.execute("UPDATE trials SET lifecycle_state='ARCHIVED'")
    page = request(application, "/review-queue")["body"]
    assert "Nothing currently needs review in this scope." in page
    assert "View project history" in page
