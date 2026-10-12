"""Active Learning review queue with uncertainty sampling and persistent JSONL storage.

Implements human-in-the-loop candidate review:
- Uncertainty sampling: uncertainty = 1.0 - min(1.0, abs(prob - 0.5) * 2.0)
- Thread-safe in-memory cache with bounded LRU eviction
- Persistent storage to JSONL (no ephemeral-only loss of human corrections)
- Exports resolved corrections as training pairs for reranker / biencoder fine-tuning
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ActiveLearningItem(BaseModel):
    """An item queued for human review due to model prediction uncertainty."""

    id: str
    query: str
    candidate_code: str
    candidate_description: str
    subcategory: str
    prob: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved: bool = False
    accepted: bool | None = None
    corrected_candidate: str | None = None


class ActiveLearningQueue:
    """Thread-safe active learning queue backed by persistent JSONL storage."""

    def __init__(
        self,
        capacity: int = 500,
        storage_path: str | Path = "data/active_learning_queue.jsonl",
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self.storage_path = Path(storage_path)
        self._items: OrderedDict[str, ActiveLearningItem] = OrderedDict()
        self._lock = RLock()
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads existing items from persistent storage if file exists."""
        with self._lock:
            if not self.storage_path.exists():
                return
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        item = ActiveLearningItem.model_validate(data)
                        self._items[item.id] = item
            except (json.JSONDecodeError, ValueError, OSError) as exc:
                logger.debug("Failed reading active learning queue file: %s", exc)

    def _sync_to_disk(self) -> None:
        """Flushes the current state of items to disk atomically."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(item.model_dump()) + "\n" for item in self._items.values())
        temp_path.replace(self.storage_path)

    def enqueue(
        self,
        query: str,
        candidate_code: str,
        candidate_description: str,
        subcategory: str,
        prob: float,
        uncertainty: float | None = None,
    ) -> ActiveLearningItem:
        """Enqueues a candidate-query pair for review, calculating uncertainty."""
        calc_uncertainty = (
            uncertainty
            if uncertainty is not None
            else 1.0 - min(1.0, abs(float(prob) - 0.5) * 2.0)
        )
        item_id = hashlib.sha256(
            json.dumps([query, candidate_code], separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        with self._lock:
            existing = self._items.get(item_id)
            if existing and existing.resolved:
                # Do not overwrite already resolved human decisions
                return existing

            item = ActiveLearningItem(
                id=item_id,
                query=query,
                candidate_code=candidate_code,
                candidate_description=candidate_description,
                subcategory=subcategory,
                prob=float(prob),
                uncertainty=float(calc_uncertainty),
            )
            self._items[item_id] = item
            self._items.move_to_end(item_id)

            # Enforce bounded capacity for unresolved items
            unresolved = [k for k, v in self._items.items() if not v.resolved]
            while len(unresolved) > self.capacity:
                oldest_key = unresolved.pop(0)
                del self._items[oldest_key]

            self._sync_to_disk()
            return item

    def observe(
        self,
        query: str,
        candidate_code: str,
        candidate_description: str,
        subcategory: str,
        prob: float,
        tier: str | None = None,
    ) -> ActiveLearningItem | None:
        """Observes a match result. Tier 1 matches are definitive and never enqueued."""
        if tier in ("Tier 1", "Tier-1"):
            return None
        return self.enqueue(
            query=query,
            candidate_code=candidate_code,
            candidate_description=candidate_description,
            subcategory=subcategory,
            prob=prob,
        )

    def get(self, item_id: str) -> ActiveLearningItem | None:
        """Retrieves an item by its hash ID."""
        with self._lock:
            return self._items.get(item_id)

    def list_items(self, unresolved_only: bool = True) -> list[ActiveLearningItem]:
        """Lists items, sorted by uncertainty descending (most uncertain first)."""
        with self._lock:
            items = list(self._items.values())
            if unresolved_only:
                items = [it for it in items if not it.resolved]
            items.sort(key=lambda x: x.uncertainty, reverse=True)
            return items

    def resolve(
        self,
        item_id: str,
        accepted: bool,
        corrected_candidate: str | None = None,
    ) -> ActiveLearningItem | None:
        """Records a human expert's decision and persists it."""
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return None
            item.resolved = True
            item.accepted = accepted
            item.corrected_candidate = corrected_candidate
            self._sync_to_disk()
            return item

    def training_examples(self) -> list[dict[str, Any]]:
        """Returns all resolved decisions as training examples."""
        with self._lock:
            examples: list[dict[str, Any]] = []
            for item in self._items.values():
                if not item.resolved or item.accepted is None:
                    continue
                examples.append(
                    {
                        "query": item.query,
                        "candidate": item.corrected_candidate or item.candidate_description,
                        "candidate_code": item.candidate_code,
                        "subcategory": item.subcategory,
                        "label": int(item.accepted),
                        "prob": item.prob,
                    }
                )
            return examples


_default_queue = ActiveLearningQueue()


def get_active_learning_queue() -> ActiveLearningQueue:
    """Returns the default singleton active learning review queue."""
    return _default_queue
