"""Development checks must be cheaper without overstating their coverage."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmarks'))
from verification_utils import TableVerifier, ReadOnlyGuard, copy_verified


def full_rows(conn):
    return list(conn.execute('SELECT * FROM records ORDER BY id'))


class VerificationToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'test.sqlite'
        self.conn = sqlite3.connect(self.db)
        self.addCleanup(self.conn.close)
        self.conn.execute('CREATE TABLE records (id INTEGER PRIMARY KEY, data BLOB)')
        self.conn.executemany('INSERT INTO records VALUES (?,?)', [(i, bytes([i])) for i in range(20)])
        self.conn.commit()

    def test_boundary_schedule_calls_full_only_first_last(self):
        verifier = TableVerifier({'records': ('id',)}, rounds=3, sample_size=4)
        with patch(__name__ + '.full_rows', wraps=full_rows) as digest:
            modes = [verifier.check(self.conn, r, digest)['mode'] for r in (0,0,1,1,2,2)]
        self.assertEqual(modes, ['full','full','sample','sample','full','full'])
        self.assertEqual(digest.call_count, 4)

    def test_full_mode_and_single_round(self):
        for mode, rounds, schedule in [('full',3,(0,1,2)), ('boundary',1,(0,0))]:
            with self.subTest(mode=mode, rounds=rounds):
                verifier = TableVerifier({'records': ('id',)}, rounds, mode=mode)
                self.assertTrue(all(verifier.check(self.conn,r,full_rows)['mode']=='full' for r in schedule))

    def test_sample_detects_change_and_exact_count(self):
        verifier = TableVerifier({'records': ('id',)},3,sample_size=4)
        verifier.check(self.conn,0,full_rows)
        self.conn.execute('UPDATE records SET data=? WHERE id=0', (b'changed',))
        with self.assertRaises(AssertionError): verifier.check(self.conn,1,full_rows)
        self.conn.rollback()
        self.conn.execute('INSERT INTO records VALUES (99,?)',(b'extra',))
        with self.assertRaises(AssertionError): verifier.check(self.conn,1,full_rows)

    def test_boundary_catches_change_outside_sample(self):
        verifier = TableVerifier({'records': ('id',)},3,sample_size=4)
        verifier.check(self.conn,0,full_rows)
        self.conn.execute('UPDATE records SET data=? WHERE id=1',(b'outside sample',))
        self.conn.commit()
        self.assertEqual(verifier.check(self.conn,1,full_rows)['mode'],'sample')
        with self.assertRaises(AssertionError): verifier.check(self.conn,2,full_rows)

    def test_sample_preserves_duplicate_keys_and_blob_values(self):
        self.conn.execute('CREATE TABLE buckets (bucket INTEGER, memory_id TEXT, data BLOB)')
        self.conn.executemany('INSERT INTO buckets VALUES (1,?,?)',[('a',b'a'),('a',b'a'),('b',b'b')])
        verifier=TableVerifier({'buckets':('bucket','memory_id')},3,sample_size=4)
        full=lambda c: list(c.execute('SELECT * FROM buckets ORDER BY 1,2,3'))
        verifier.check(self.conn,0,full)
        self.conn.execute("UPDATE buckets SET data=x'63' WHERE memory_id='a'")
        with self.assertRaises(AssertionError): verifier.check(self.conn,1,full)

    def test_empty_table_and_single_sample(self):
        self.conn.execute('DELETE FROM records')
        verifier=TableVerifier({'records':('id',)},3,sample_size=1)
        verifier.check(self.conn,0,full_rows)
        self.assertEqual(verifier.check(self.conn,1,full_rows)['snapshot']['records']['rows'],0)
        self.conn.execute("INSERT INTO records VALUES (1,x'61')")
        with self.assertRaises(AssertionError): verifier.check(self.conn,1,full_rows)

    def test_readonly_select_passes_update_and_rollback_fail(self):
        with ReadOnlyGuard(self.conn): self.conn.execute('SELECT * FROM records').fetchall()
        with self.assertRaises(AssertionError):
            with ReadOnlyGuard(self.conn):
                self.conn.execute("UPDATE records SET data=x'61' WHERE id=0")
                self.conn.rollback()

    def test_readonly_guard_catches_ddl_and_external_commit(self):
        with self.assertRaises(AssertionError):
            with ReadOnlyGuard(self.conn): self.conn.execute('CREATE TABLE extra (id INTEGER)')
        self.conn.commit()
        with closing(sqlite3.connect(self.db)) as other:
            with self.assertRaises(AssertionError):
                with ReadOnlyGuard(self.conn):
                    other.execute("UPDATE records SET data=x'61' WHERE id=0")
                    other.commit()

    def test_invalid_schedule_and_identifiers(self):
        for kwargs in ({'rounds':0}, {'rounds':2,'mode':'unknown'}, {'rounds':2,'sample_size':0}):
            with self.assertRaises(ValueError): TableVerifier({'records':('id',)},**kwargs)
        with self.assertRaises(ValueError): TableVerifier({'records;DROP':('id',)},2)
        verifier=TableVerifier({'records':('id',)},2)
        with self.assertRaises(ValueError): verifier.check(self.conn,2,full_rows)

    def test_copy_verifies_once_and_refuses_overwrite(self):
        src=Path(self.tmp.name)/'source'; dst=Path(self.tmp.name)/'copy'
        src.write_bytes(b'payload' * 30000)
        with patch('verification_utils.file_sha256', wraps=__import__('verification_utils').file_sha256) as digest:
            receipt=copy_verified(src,dst)
        self.assertEqual(src.read_bytes(),dst.read_bytes())
        self.assertEqual(receipt['sha256'],hashlib.sha256(src.read_bytes()).hexdigest())
        self.assertEqual(receipt['bytes'],src.stat().st_size)
        self.assertEqual(digest.call_count,1)
        self.assertEqual(Path(digest.call_args.args[0]),dst)
        with self.assertRaises(FileExistsError): copy_verified(src,dst)
        with self.assertRaises(FileExistsError): copy_verified(src,src)

    def test_copy_detects_corrupt_target_and_cleans_only_created_file(self):
        src=Path(self.tmp.name)/'source'; dst=Path(self.tmp.name)/'copy'; src.write_bytes(b'ok')
        def corrupt(path):
            Path(path).write_bytes(b'bad')
            return hashlib.sha256(b'bad').hexdigest()
        with patch('verification_utils.file_sha256',side_effect=corrupt):
            with self.assertRaises(AssertionError): copy_verified(src,dst)
        self.assertFalse(dst.exists()); self.assertEqual(src.read_bytes(),b'ok')

    def test_copy_detects_source_change(self):
        src=Path(self.tmp.name)/'source'; dst=Path(self.tmp.name)/'copy'; src.write_bytes(b'ok')
        def mutate(path):
            src.write_bytes(b'changed after copy')
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()
        with patch('verification_utils.file_sha256',side_effect=mutate):
            with self.assertRaises(AssertionError): copy_verified(src,dst)
        self.assertFalse(dst.exists())

if __name__=='__main__': unittest.main()
