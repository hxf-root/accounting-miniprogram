"""Source-neutral photo sync planning; no filesystem, network or database access.

Android is responsible for reading only user-selected albums. The planner never
infers deletions from a scan: permissions and files can disappear temporarily.
"""
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PhotoCandidate:
    album_id: str
    item_id: str
    revision: str


@dataclass(frozen=True)
class PlannedPhoto:
    album_id: str
    item_id: str
    revision: str


def plan_photo_uploads(selected_albums: Iterable[str], candidates: Iterable[PhotoCandidate],
                       uploaded_revisions: dict[tuple[str, str], str]) -> list[PlannedPhoto]:
    """Return new/changed photos from the explicitly selected album IDs only.

    Revision must represent content or provider generation, not merely a display
    name. Callers persist the acknowledged revision only after a successful upload.
    A missing candidate never triggers a remote deletion.
    """
    selected = set(selected_albums)
    if any(not isinstance(album, str) or not album.strip() for album in selected):
        raise ValueError('selected album identifiers must be non-empty strings')
    seen: set[tuple[str, str]] = set()
    planned: list[PlannedPhoto] = []
    for candidate in candidates:
        if not isinstance(candidate, PhotoCandidate):
            raise ValueError('invalid photo candidate')
        if any(not isinstance(value, str) or not value.strip()
               for value in (candidate.album_id, candidate.item_id, candidate.revision)):
            raise ValueError('photo identifiers and revision must be non-empty strings')
        key = (candidate.album_id, candidate.item_id)
        if key in seen:
            raise ValueError('duplicate photo identifier in scan')
        seen.add(key)
        if candidate.album_id in selected and uploaded_revisions.get(key) != candidate.revision:
            planned.append(PlannedPhoto(candidate.album_id, candidate.item_id, candidate.revision))
    return planned
