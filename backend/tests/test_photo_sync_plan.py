"""Photo planning is independent of Android, storage and network implementations."""
import pytest
from integrations.photo_sync_plan import PhotoCandidate, PlannedPhoto, plan_photo_uploads


def test_only_selected_albums_are_planned_and_unchanged_items_skipped():
    candidates = [PhotoCandidate('camera', '1', 'v1'), PhotoCandidate('camera', '2', 'v2'),
                  PhotoCandidate('private', '3', 'v1')]
    plan = plan_photo_uploads(['camera'], candidates, {('camera', '1'): 'v1', ('camera', '2'): 'v1'})
    assert plan == [PlannedPhoto('camera', '2', 'v2')]
    assert plan_photo_uploads([], candidates, {}) == []


def test_partial_scan_never_creates_a_deletion_or_changes_state():
    uploaded = {('camera', 'previous'): 'v1'}
    assert plan_photo_uploads(['camera'], [], uploaded) == []
    assert uploaded == {('camera', 'previous'): 'v1'}


def test_invalid_and_duplicate_records_fail_before_returning_a_plan():
    with pytest.raises(ValueError):
        plan_photo_uploads(['camera'], [PhotoCandidate('camera', '1', '')], {})
    with pytest.raises(ValueError):
        plan_photo_uploads(['camera'], [PhotoCandidate('camera', '1', 'a'), PhotoCandidate('camera', '1', 'b')], {})
    with pytest.raises(ValueError):
        plan_photo_uploads([''], [], {})
