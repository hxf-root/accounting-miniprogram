"""Private, bounded filesystem blob storage. Not wired to an HTTP endpoint.

The caller must authenticate users and persist/backup metadata separately. This
module preserves original bytes, including any EXIF metadata, and never infers
file deletion from an incomplete sync.
"""
import hashlib
import os
import re
import stat
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

_ID = re.compile(r'^[0-9a-f]{32}$')
_MAX_SIZE = 20 * 1024 * 1024


@dataclass(frozen=True)
class StoredPhoto:
    photo_id: str
    size: int
    sha256: str


def _private_dir(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('photo directory must be owned and private')


class PhotoStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.is_absolute():
            raise ValueError('photo storage path must be absolute')
        _private_dir(self.root)

    def _user_dir(self, user_id: int, *, create: bool = False) -> Path:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise ValueError('invalid user')
        _private_dir(self.root)
        path = self.root / str(user_id)
        if create:
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                pass
        _private_dir(path)
        return path

    def save(self, user_id: int, stream: BinaryIO, *, max_size: int = _MAX_SIZE) -> StoredPhoto:
        if not isinstance(max_size, int) or isinstance(max_size, bool) or not 1 <= max_size <= _MAX_SIZE:
            raise ValueError('invalid size limit')
        directory = self._user_dir(user_id, create=True)
        fd, name = tempfile.mkstemp(prefix='.upload-', dir=directory)
        size = 0
        digest = hashlib.sha256()
        photo_id = uuid.uuid4().hex
        try:
            with os.fdopen(fd, 'wb') as out:
                while True:
                    chunk = stream.read(min(65536, max_size + 1 - size))
                    if not isinstance(chunk, bytes):
                        raise ValueError('photo stream must return bytes')
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_size:
                        raise ValueError('photo exceeds size limit')
                    digest.update(chunk)
                    out.write(chunk)
                if not size:
                    raise ValueError('empty photo')
                out.flush()
                os.fsync(out.fileno())
            # Hard-link fails if the identifier already exists; never overwrite.
            os.link(name, directory / photo_id, follow_symlinks=False)
            return StoredPhoto(photo_id, size, digest.hexdigest())
        finally:
            os.unlink(name)

    def open(self, user_id: int, photo_id: str) -> BinaryIO:
        if not isinstance(photo_id, str) or not _ID.fullmatch(photo_id):
            raise ValueError('invalid photo identifier')
        directory = self._user_dir(user_id)
        fd = os.open(directory / photo_id, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError('photo file must be owned and private')
            return os.fdopen(fd, 'rb')
        except BaseException:
            os.close(fd)
            raise

    def delete(self, user_id: int, photo_id: str) -> None:
        if not isinstance(photo_id, str) or not _ID.fullmatch(photo_id):
            raise ValueError('invalid photo identifier')
        directory = self._user_dir(user_id)
        os.unlink(directory / photo_id)
