from app.services.voc_coding_chain_service import (
    VocCodingChainError,
    _init_checkpoint_state,
    determine_batch_strategy,
    finalize_checkpoint,
    load_checkpoint,
    merge_coded_reviews_into_rows,
    save_checkpoint,
    validate_import_ready_rows,
)


class DummySettings:
    voc_coding_checkpoint_dir = ""


def test_determine_batch_strategy():
    strategy = determine_batch_strategy(total_reviews=203, batch_size=20, discovery_cap=100)
    assert strategy["discovery_sample_size"] == 100
    assert strategy["coding_batch_size"] == 20
    assert strategy["total_coding_batches"] == 11


def test_merge_coded_reviews_into_rows():
    rows = [
        {"respondent_id": "tp_1", "topics": [], "overall_sentiment": None, "processed": False},
        {"respondent_id": "tp_2", "topics": [], "overall_sentiment": None, "processed": False},
    ]
    coded = [
        {
            "respondent_id": "tp_1",
            "overall_sentiment": "positive",
            "topics": [{"category": "Delivery", "label": "Fast", "code": "delivery_fast", "sentiment": "positive"}],
        }
    ]

    merged = merge_coded_reviews_into_rows(rows, coded)
    assert merged[0]["processed"] is True
    assert merged[0]["overall_sentiment"] == "positive"
    assert merged[1]["processed"] is False


def test_validate_import_ready_rows_rejects_duplicates():
    rows = [
        {
            "respondent_id": "tp_1",
            "overall_sentiment": "positive",
            "topics": [{"category": "Delivery", "label": "Fast", "code": "delivery_fast", "sentiment": "positive"}],
        },
        {
            "respondent_id": "tp_1",
            "overall_sentiment": "negative",
            "topics": [{"category": "Delivery", "label": "Slow", "code": "delivery_slow", "sentiment": "negative"}],
        },
    ]
    try:
        validate_import_ready_rows(rows)
        assert False, "Expected VocCodingChainError for duplicate respondent_id"
    except VocCodingChainError as exc:
        assert exc.step == "validate"


def test_checkpoint_save_load_finalize(tmp_path):
    settings = DummySettings()
    settings.voc_coding_checkpoint_dir = str(tmp_path)

    state = _init_checkpoint_state(
        run_id="run_abc",
        total_reviews=5,
        strategy={"coding_batch_size": 2, "total_coding_batches": 3},
    )
    save_checkpoint(settings, state)

    loaded = load_checkpoint(settings, "run_abc")
    assert loaded is not None
    assert loaded["run_id"] == "run_abc"
    assert loaded["status"] == "in_progress"

    finalize_checkpoint(settings, loaded)
    completed = load_checkpoint(settings, "run_abc")
    assert completed is not None
    assert completed["status"] == "completed"
