"""Fixed, explicitly supplied annotations for tests; no external inference."""
from threading import RLock

from mnemosis.evidence_annotation import ModelReply, SupportBatchReply, SupportReplies
from mnemosis.types import MemoryItem, MemoryKind, RecallResult, SourceRecord, SourceType


def reply(payload=None, error=None):
    return ModelReply(payload, None, None, 0, error)


class FixedAnnotator:
    budget_seconds = 60.0

    def __init__(self, *, scope="finite", roles=("destination", "date"), rows=None,
                 plan_error=None, batch_error=None, hook=None):
        self.scope, self.roles, self.rows = scope, roles, rows
        self.plan_error, self.batch_error, self.hook = plan_error, batch_error, hook
        self.calls = []

    def plan(self, query, *, deadline):
        self.calls.append(("plan", query, deadline))
        if self.hook:
            self.hook()
        return reply({"scope": self.scope, "aspects": list(self.roles)}, self.plan_error)

    def support(self, query, aspects, source_texts, *, deadline):
        self.calls.append(("support", query, deadline))
        rows = self.rows
        if rows is None:
            rows = []
            for memory_id, text in source_texts.items():
                for a in aspects:
                    quote = "Osaka" if a.aspect_id == "a0" else "October"
                    positive = quote in text
                    rows.append(dict(memory_id=memory_id, aspect_id=a.aspect_id,
                                     verdict="supported" if positive else "not_supported",
                                     quote=quote if positive else None))
        return SupportReplies((SupportBatchReply(tuple(source_texts),
                              reply({"decisions": rows}, self.batch_error)),), ())


def results():
    return [RecallResult(MemoryItem(id=key, content=text, kind=MemoryKind.EPISODIC,
                                   source=SourceRecord(SourceType.USER)), 100 - i, [key], False)
            for i, (key, text) in enumerate((("A", "Mina went to Osaka."),
                                             ("B", "The trip destination was Osaka."),
                                             ("C", "The trip was in October.")))]


class FrozenEngine:
    def __init__(self, rows=None):
        self.rows = results() if rows is None else rows
        self._lock = RLock()
        self.calls = []
        self._default_embedder = None
        self.store = type("Store", (), {"_vector_index": None, "_index_embedder": None})()

    def recall(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return self.rows[:kwargs["top_k"]]
