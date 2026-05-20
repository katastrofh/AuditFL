from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ArtifactUnavailable(Exception):
    pass


@dataclass
class ContentAddressedStore:
    root: Path
    fail_rate: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        import random
        self._rng = random.Random(self.seed)
        self.put_count = 0
        self.get_count = 0
        self.get_failures = 0

    @staticmethod
    def _cid(data: bytes) -> str:
        return "sha256:" + hashlib.sha256(data).hexdigest()

    def put_bytes(self, data: bytes) -> str:
        cid = self._cid(data)
        (self.root / cid.replace(":", "_")).write_bytes(data)
        self.put_count += 1
        return cid

    def get_bytes(self, cid: str) -> bytes:
        self.get_count += 1
        if self.fail_rate > 0 and self._rng.random() < self.fail_rate:
            self.get_failures += 1
            raise ArtifactUnavailable(f"injected artifact get failure for {cid}")
        path = self.root / cid.replace(":", "_")
        if not path.exists():
            self.get_failures += 1
            raise ArtifactUnavailable(f"missing artifact {cid}")
        data = path.read_bytes()
        if self._cid(data) != cid:
            self.get_failures += 1
            raise ArtifactUnavailable(f"integrity check failed for {cid}")
        return data

    def put_obj(self, obj: Any) -> str:
        return self.put_bytes(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))

    def get_obj(self, cid: str) -> Any:
        return pickle.loads(self.get_bytes(cid))
