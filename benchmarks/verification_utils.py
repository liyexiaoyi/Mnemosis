"""Bounded verification for local developer evaluations and static archives.

Sampling is not exhaustive equality. ReadOnlyGuard detects counted DML (even
rolled back), committed external changes and schema/transaction state changes;
it is a diagnostic, not a security sandbox or proof against transient DDL.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re


def _identifier(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value):
        raise ValueError('invalid SQLite identifier')
    return '"' + value + '"'


def _json_rows(rows):
    return json.dumps([tuple(row) for row in rows], ensure_ascii=True,
                      separators=(',', ':'), default=lambda value: {'blob_hex': value.hex()})


class TableVerifier:
    """First/last full digests; intermediate exact counts and fixed key samples.

    Keys must identify rows, or groups of duplicate rows. Both variants share
    the same verifier and frozen baseline keys. Queries compare every column.
    """
    def __init__(self, tables, rounds, mode='boundary', sample_size=32):
        if rounds < 1 or mode not in ('boundary', 'full') or sample_size < 1:
            raise ValueError('invalid verification configuration')
        self.tables = {table: tuple(keys) for table, keys in tables.items()}
        if not self.tables or any(not keys for keys in self.tables.values()):
            raise ValueError('tables and keys must be nonempty')
        for table, keys in self.tables.items():
            _identifier(table)
            for key in keys: _identifier(key)
        self.rounds, self.mode, self.sample_size = rounds, mode, sample_size
        self.keys = None
        self.expected_full = self.expected_sample = None

    def _sample(self, conn):
        result = {}
        initialize = self.keys is None
        if initialize: self.keys = {}
        for table, columns in self.tables.items():
            name = _identifier(table)
            schema = conn.execute(f'PRAGMA table_info({name})').fetchall()
            names = [row[1] for row in schema]
            if not set(columns).issubset(names): raise ValueError('sample key missing from table')
            count = conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            key_sql = ','.join(_identifier(c) for c in columns)
            if initialize:
                size = min(count, self.sample_size)
                offsets = [i*(count-1)//max(1,size-1) for i in range(size)]
                self.keys[table] = list(dict.fromkeys(tuple(conn.execute(
                    f'SELECT {key_sql} FROM {name} ORDER BY {key_sql} LIMIT 1 OFFSET ?',
                    (offset,)).fetchone()) for offset in offsets))
            where = ' AND '.join(_identifier(c)+' IS ?' for c in columns)
            order = ','.join(_identifier(c) for c in names)
            samples = [_json_rows(conn.execute(f'SELECT * FROM {name} WHERE {where} ORDER BY {order}', key))
                       for key in self.keys[table]]
            result[table] = dict(rows=count, schema=[tuple(row) for row in schema], samples=samples)
        return result

    def check(self, conn, round_id, full_digest):
        if not 0 <= round_id < self.rounds: raise ValueError('round outside schedule')
        full = self.mode == 'full' or round_id in (0, self.rounds-1)
        if self.expected_sample is None:
            if not full: raise ValueError('first check must be a full boundary')
            self.expected_sample = self._sample(conn)
        if full:
            snapshot = full_digest(conn)
            if self.expected_full is None: self.expected_full = snapshot
            assert snapshot == self.expected_full, 'full persisted-state comparison failed'
        else:
            snapshot = self._sample(conn)
            assert snapshot == self.expected_sample, 'sample/count/schema comparison failed'
        return dict(mode='full' if full else 'sample', snapshot=snapshot)


class ReadOnlyGuard:
    """Cheap query-write diagnostic; no table scanning or content hashing."""
    def __init__(self, conn): self.conn = conn

    def _state(self):
        return (self.conn.total_changes,
                self.conn.execute('PRAGMA data_version').fetchone()[0],
                self.conn.execute('PRAGMA schema_version').fetchone()[0],
                self.conn.execute('PRAGMA temp.schema_version').fetchone()[0],
                self.conn.in_transaction)

    def __enter__(self):
        self.before = self._state()
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            assert self._state() == self.before, 'read-only query changed SQLite state'
        return False


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()


def _file_version(path):
    st = Path(path).stat()
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def copy_verified(source, target):
    """Copy a quiescent file, hashing its stream and reading the target once.

    Refuses replacement. Metadata detects ordinary source changes, but is not
    an atomic snapshot or protection against deliberate metadata restoration.
    Removes only the newly created target if copying/verification fails.
    """
    source, target = Path(source), Path(target)
    before = _file_version(source)
    digest = hashlib.sha256()
    count = 0
    created = False
    try:
        with source.open('rb') as incoming, target.open('xb') as outgoing:
            created = True
            for chunk in iter(lambda: incoming.read(1024*1024), b''):
                outgoing.write(chunk); digest.update(chunk); count += len(chunk)
            outgoing.flush(); os.fsync(outgoing.fileno())
        expected = digest.hexdigest()
        assert file_sha256(target) == expected, 'archive target digest mismatch'
        assert _file_version(source) == before and count == before[2], 'source changed during copy'
        return dict(bytes=count, sha256=expected)
    except BaseException:
        if created: target.unlink(missing_ok=True)
        raise
