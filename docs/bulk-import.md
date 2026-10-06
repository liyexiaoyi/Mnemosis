# Bulk import performance and failure boundaries

The graph builders retain the same directed pair set, but emit reciprocal pairs
adjacently. SQLite bulk staging skips identical adjacent canonical rows, so the
normal association import writes each undirected edge once per generated batch.
This reduces staging, sorting and repeated MAX upserts without a whole-input
hash table. Different weights and non-adjacent duplicates still use the existing
MAX merge. Normal-mode backend transaction chunk boundaries are retained; the
unordered association pair list now has reciprocal directions grouped.

The cue frequency filter, latest-neighbor choice, link budget, memory contents,
sequence allocation, and final association graph are unchanged. Pure Python and
optional Rust BM25 remain usable; no new native extension is required. This is
an import optimization, not a retrieval accuracy change.

## Failure and retry

Both `remember_many` and `remember_many_chunked` now check embedding result
cardinality before writing the current batch. An embedding API exception or a
wrong number of vectors leaves that batch unwritten. Successful earlier chunks
remain committed; only a verified unwritten suffix can be retried safely.

Neither method is globally atomic on SQLite: storage uses bounded transactions.
A storage, graph, vector dimension/index, or bulk-finalization failure can leave
partial writes. This change does not supply a persistent checkpoint, import ID,
or automatic full-input idempotence. Replaying all episodic records creates new
memories; inspect/reconcile persisted data before doing so. Semantic dedup is a
separate existing mechanism and can strengthen evidence on replay.

The association pool is released even if bulk finalization raises. Database
recovery errors still propagate; releasing the pool does not prove failed index
restoration succeeded. Existing bulk mode remains single-writer, stages links
and terms until finalization, and temporarily weakens durability. No durability
or concurrency setting was relaxed further in this change.

## Reproduce local paired measurements

Use a trusted pre-change Git source archive:

```powershell
python benchmarks/ingest_pair_eval.py --baseline-archive E:/Mnemosis/backups/2026-10-06-ingest-before/repository.zip --out E:/Mnemosis/evaluation/ingest/2026-10-06/example-new --count 10000 --mode chunked --workload linked --rounds 7
```

The harness loads the old graph and link methods from the archive, then alternates
old/new implementations in the same process and current engine. Preparation,
engine opening, verification, recall, closing, and explicit collection are
outside the import timer. Timing includes complete linking, SQLite insertion,
final copying/index recreation/checkpointing, and one staged-row count inspection
per bulk import. All wall and CPU samples are saved, with full database/graph,
returned-ID-order and recall equality checks. Only the final pair of synthetic
databases is retained; all earlier sample records and signatures are retained.

Unique episodic inputs, fixed timestamps and random seeded UUIDs, explicit cues
(group size 64 or unique), auto-cues/context disabled, no embedding calls; OS
cache and host background load are uncontrolled. Different import modes can
build different graphs and have different durability, so their diagnostic
comparison is not a substitutable promise. Gains depend on association density.

Results and limits: E:/Mnemosis/eleventh-batch-report-2026-10-06.md.
Raw measurements: E:/Mnemosis/evaluation/ingest/2026-10-06.
