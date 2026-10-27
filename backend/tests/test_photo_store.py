import io
import os
import pytest
from integrations.photo_store import PhotoStore


def test_isolation_and_delete(tmp_path):
    root = tmp_path / 'photos'
    root.mkdir(mode=0o700)
    store = PhotoStore(root)
    item = store.save(1, io.BytesIO(b'synthetic image bytes'))
    with store.open(1, item.photo_id) as photo:
        assert photo.read() == b'synthetic image bytes'
    assert item.size == 21
    store.save(2, io.BytesIO(b'other'))
    with pytest.raises(FileNotFoundError):
        store.open(2, item.photo_id)
    assert os.stat(root / '1' / item.photo_id).st_mode & 0o777 == 0o600
    store.delete(1, item.photo_id)
    with pytest.raises(FileNotFoundError):
        store.open(1, item.photo_id)


def test_failure_leaves_no_partial_file(tmp_path):
    root = tmp_path / 'photos'
    root.mkdir(mode=0o700)
    store = PhotoStore(root)
    with pytest.raises(ValueError):
        store.save(1, io.BytesIO(b'12345'), max_size=4)
    with pytest.raises(ValueError):
        store.save(1, io.BytesIO(b''))
    assert list((root / '1').iterdir()) == []


def test_rejects_unsafe_paths_and_permissions(tmp_path):
    root = tmp_path / 'photos'
    root.mkdir(mode=0o700)
    store = PhotoStore(root)
    with pytest.raises(ValueError):
        store.save(-1, io.BytesIO(b'x'))
    with pytest.raises(ValueError):
        store.open(1, '../1')
    (root / '1').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        store.save(1, io.BytesIO(b'x'))
    root.chmod(0o755)
    with pytest.raises(ValueError):
        PhotoStore(root)
