import hashlib
from uuid import UUID


def is_in_stable_rollout(conversation_id: UUID | str, percent: int) -> bool:
    normalized_percent = max(0, min(int(percent), 100))
    if normalized_percent == 0:
        return False
    if normalized_percent == 100:
        return True
    digest = hashlib.sha256(str(conversation_id).encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], byteorder="big") % 100
    return bucket < normalized_percent
