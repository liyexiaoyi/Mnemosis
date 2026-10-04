"""Source event indexes must avoid full scans without losing timeline correctness."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from mnemosis import MemoryEngine
from mnemosis.schema import EventChainIndex
import mnemosis.schema as schema
from mnemosis.types import MemoryKind,MemoryStatus,SourceRecord,SourceType

NOW=datetime(2026,10,4,12,tzinfo=timezone.utc)

class SourceIndexTests(unittest.TestCase):
    def build(self,disk=True):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        path=str(Path(folder.name)/'memory.db') if disk else None
        engine=MemoryEngine(path,auto_warmup=False);self.addCleanup(engine.close)
        items=engine.remember_many([dict(content=text,kind=MemoryKind.EPISODIC,
            source=SourceRecord(SourceType.USER,occurred_at=datetime(2026,1,i+1,10,tzinfo=timezone.utc)),
            cues=['alice','session1'],created_at=NOW) for i,text in enumerate(['anchorneedle aquarium','destination tacos','evening walk'])],
            auto_cues=False,auto_context=False)
        return engine,path,items

    def change_date(self,e,item,day):
        current=e.backend.get(item.id)
        current.source.occurred_at=datetime(2026,1,day,10,tzinfo=timezone.utc)
        e.backend.update(current)

    def assert_matches_fresh(self,e,chain,items):
        fresh=EventChainIndex(e.backend,date_policy='source',event_timezone=chain.event_timezone)
        self.assertEqual([chain.next_event_id(i.id) for i in items],[fresh.next_event_id(i.id) for i in items])
        self.assertEqual(chain.chain_length(),fresh.chain_length())

    def source_json(self,e,item,day):
        value=e.backend.get(item.id).source.to_dict()
        value['occurred_at']=datetime(2026,1,day,10,tzinfo=timezone.utc).isoformat()
        return json.dumps(value)

    def test_sqlite_unchanged_chain_does_not_reload_or_resolve(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source')
        self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan,patch.object(schema,'resolve_event_time',wraps=schema.resolve_event_time) as resolve:
            for _ in range(5):self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
            self.assertEqual(scan.call_count,0)
            self.assertEqual(resolve.call_count,0)

    def test_source_only_edit_resolves_changed_item_without_full_scan(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source')
        chain.next_event_id(items[0].id);lexical=e.backend.revision_token()
        self.change_date(e,items[1],4)
        self.assertEqual(e.backend.revision_token(),lexical)
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan,patch.object(schema,'resolve_event_time',wraps=schema.resolve_event_time) as resolve:
            self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
            self.assertEqual(scan.call_count,0)
            self.assertEqual([c.args[0].id for c in resolve.call_args_list],[items[1].id])
        self.assert_matches_fresh(e,chain,items)

    def test_public_source_recall_reuses_chain_and_is_read_only(self):
        e,_,_=self.build()
        def recall():return e.recall('anchorneedle',top_k=5,now=NOW,read_only=True,temporal_policy='source',pattern_completion=False,concept_coverage=False)
        first=recall();before=json.dumps([i.to_dict() for i in e.store.all_active()],sort_keys=True)
        links=sorted(e.backend.all_links());log=e.get_recall_log()
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan:
            second=recall();self.assertEqual(scan.call_count,0)
        signature=lambda rows:[(r.item.id,r.score,r.confident,tuple(r.reasons)) for r in rows]
        self.assertEqual(signature(first),signature(second))
        self.assertEqual(before,json.dumps([i.to_dict() for i in e.store.all_active()],sort_keys=True))
        self.assertEqual(links,sorted(e.backend.all_links()));self.assertEqual(log,e.get_recall_log())

    def test_external_source_edit_is_incremental(self):
        e,path,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute('UPDATE memories SET source_json=? WHERE id=?',(self.source_json(e,items[1],4),items[1].id))
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan:
            self.assertEqual(chain.next_event_id(items[0].id),items[2].id);self.assertEqual(scan.call_count,0)
        self.assert_matches_fresh(e,chain,items)

    def test_rollback_and_new_branch_never_reuse_uncommitted_timeline(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        connection=e.backend._conn
        connection.execute('UPDATE memories SET source_json=? WHERE id=?',(self.source_json(e,items[1],4),items[1].id))
        self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
        connection.rollback();self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
        connection.execute('UPDATE memories SET source_json=? WHERE id=?',(self.source_json(e,items[2],5),items[2].id));connection.commit()
        self.assert_matches_fresh(e,chain,items)

    def test_insert_delete_forget_restore_match_full_rebuild(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        added=e.remember('new visit',kind=MemoryKind.EPISODIC,cues=['alice','session1'],
            source=SourceRecord(SourceType.USER,occurred_at=datetime(2026,1,1,11,tzinfo=timezone.utc)),auto_cues=False,auto_context=False)
        all_items=items+[added]
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan:
            self.assertEqual(chain.next_event_id(items[0].id),added.id);self.assertEqual(scan.call_count,0)
        for operation in [lambda:e.forget(added.id),lambda:e.restore(added.id),lambda:e.backend.delete(added.id)]:
            operation();self.assert_matches_fresh(e,chain,all_items)

    def test_group_move_and_kind_change_remove_old_successors(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        item=e.backend.get(items[1].id);item.cues=['bob','session2'];e.backend.update(item)
        self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
        with e.backend._conn:
            e.backend._conn.execute("UPDATE memories SET kind='semantic' WHERE id=?",(items[2].id,))
        self.assertIsNone(chain.next_event_id(items[0].id));self.assertEqual(chain.chain_length(),0)
        self.assert_matches_fresh(e,chain,items)

    def test_reinforcement_changes_do_not_invalidate_source_index(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        item=e.backend.get(items[1].id);item.strength+=1;item.access_count+=1;e.backend.update(item)
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan,patch.object(schema,'resolve_event_time',wraps=schema.resolve_event_time) as resolve:
            self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
            self.assertEqual(scan.call_count,0);self.assertEqual(resolve.call_count,0)

    def test_ambiguous_content_edit_drops_only_changed_event(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        e.update(items[1].id,content='2026年1月2日 lunch and 2026年1月3日 dinner')
        with patch.object(schema,'resolve_event_time',wraps=schema.resolve_event_time) as resolve:
            self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
            self.assertEqual(resolve.call_count,1)
        self.assert_matches_fresh(e,chain,items)

    def test_timezone_change_rebuilds_calendar_interpretation(self):
        e,_,items=self.build()
        a=e.backend.get(items[0].id);a.content='2026-01-02 aquarium';a.source.occurred_at=None;e.backend.update(a)
        b=e.backend.get(items[1].id);b.source.occurred_at=datetime(2026,1,1,20,tzinfo=timezone.utc);e.backend.update(b)
        chain=EventChainIndex(e.backend,date_policy='source')
        self.assertEqual(chain.next_event_id(b.id),a.id)
        chain.event_timezone=timezone(timedelta(hours=8))
        self.assertEqual(chain.next_event_id(a.id),b.id)
        self.assert_matches_fresh(e,chain,items)

    def test_dict_direct_nested_source_cue_and_status_mutations_remain_visible(self):
        e,_,items=self.build(False);chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        items[1].source.occurred_at=datetime(2026,1,4,10,tzinfo=timezone.utc)
        self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
        items[1].cues[0]='bob';items[2].status=MemoryStatus.RECYCLED
        self.assertIsNone(chain.next_event_id(items[0].id))
        self.assert_matches_fresh(e,chain,items)

    def test_missing_or_excessive_history_falls_back_to_fresh_chain(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        connection=e.backend._conn
        with connection:
            connection.executemany('UPDATE memories SET source_json=? WHERE id=?',[(self.source_json(e,items[1],4 if i%2 else 5),items[1].id) for i in range(5000)])
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan:
            self.assertEqual(chain.next_event_id(items[0].id),items[2].id);self.assertEqual(scan.call_count,1)
        count=connection.execute('SELECT COUNT(*) FROM source_event_changes').fetchone()[0]
        self.assertLessEqual(count,4351)
        self.assert_matches_fresh(e,chain,items)

    def test_revision_gap_is_not_mistaken_for_known_delta(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        token_method=getattr(e.backend,'event_revision_token',None)
        self.assertIsNotNone(token_method,'backend has no source-aware revision contract')
        with e.backend._conn:
            e.backend._conn.execute('UPDATE source_event_state SET revision=randomblob(16) WHERE id=1')
        self.change_date(e,items[1],4)
        with patch.object(e.backend,'list_items',wraps=e.backend.list_items) as scan:
            self.assertEqual(chain.next_event_id(items[0].id),items[2].id);self.assertEqual(scan.call_count,1)

    def test_failed_resolver_does_not_publish_partial_index(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        self.change_date(e,items[1],4)
        with patch.object(schema,'resolve_event_time',side_effect=RuntimeError('resolver failed')):
            with self.assertRaises(RuntimeError):chain.next_event_id(items[0].id)
        self.assert_matches_fresh(e,chain,items)

    def test_change_during_delta_read_is_not_tagged_with_new_revision(self):
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source');chain.next_event_id(items[0].id)
        self.change_date(e,items[1],4);original=e.backend.get_many
        def raced(ids):
            rows=original(ids);self.change_date(e,items[0],5);return rows
        with patch.object(e.backend,'get_many',side_effect=raced):
            self.assertIsNone(chain.next_event_id(items[0].id),'racing delta must fall back to a coherent full snapshot')
        self.assertIsNone(chain.next_event_id(items[0].id))
        self.assert_matches_fresh(e,chain,items)

    def test_upgrade_adds_event_tracking_without_changing_memory_data(self):
        e,path,items=self.build();before=[i.to_dict() for i in e.store.all_active()];e.close()
        with closing(sqlite3.connect(path)) as connection, connection:
            for event in ('insert','delete','update'):connection.execute(f'DROP TRIGGER IF EXISTS source_event_{event}_v1')
            connection.execute('DROP TABLE IF EXISTS source_event_changes');connection.execute('DROP TABLE IF EXISTS source_event_state')
        reopened=MemoryEngine(path,auto_warmup=False);self.addCleanup(reopened.close)
        self.assertEqual([i.to_dict() for i in reopened.store.all_active()],before)
        chain=EventChainIndex(reopened.backend,date_policy='source');chain.next_event_id(items[0].id)
        with patch.object(reopened.backend,'list_items',wraps=reopened.backend.list_items) as scan:
            chain.next_event_id(items[0].id);self.assertEqual(scan.call_count,0)

    def test_equal_instants_follow_updated_sequence_order(self):
        e,_,items=self.build();self.change_date(e,items[1],1)
        chain=EventChainIndex(e.backend,date_policy='source')
        self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
        with e.backend._conn:
            e.backend._conn.execute('UPDATE memories SET seq=100 WHERE id=?',(items[0].id,))
        self.assertEqual(chain.next_event_id(items[1].id),items[0].id)
        self.assert_matches_fresh(e,chain,items)

    def test_public_timezone_switch_uses_correct_successor(self):
        e,_,items=self.build()
        a=e.backend.get(items[0].id);a.content='2026-01-02 anchorneedle aquarium';a.source.occurred_at=None;e.backend.update(a)
        b=e.backend.get(items[1].id);b.source.occurred_at=datetime(2026,1,1,20,tzinfo=timezone.utc);e.backend.update(b)
        for zone in (timezone.utc,timezone(timedelta(hours=8)),timezone.utc):
            rows=e.recall('anchorneedle',top_k=5,now=NOW.astimezone(zone),read_only=True,
                temporal_policy='source',pattern_completion=False,concept_coverage=False)
            expected=EventChainIndex(e.backend,date_policy='source',event_timezone=zone).next_event_id(a.id)
            self.assertTrue(any(r.item.id==expected and any('时序后继' in reason for reason in r.reasons) for r in rows))

    def test_seeded_event_mutations_match_complete_rebuild(self):
        import random
        e,_,items=self.build();chain=EventChainIndex(e.backend,date_policy='source')
        rng=random.Random(9421)
        for step in range(70):
            item=e.backend.get(rng.choice(items).id)
            operation=step%5
            if operation==0:item.source.occurred_at=datetime(2026,1,rng.randint(1,28),rng.randint(0,23),tzinfo=timezone.utc)
            elif operation==1:item.cues=[rng.choice(['alice','bob','carol']),'session1']
            elif operation==2:item.content='unknown visit' if step%2 else '2026-01-01 and 2026-01-02 visit'
            elif operation==3:item.status=MemoryStatus.ACTIVE if item.status is MemoryStatus.RECYCLED else MemoryStatus.RECYCLED
            else:item.strength+=0.1
            e.backend.update(item)
            self.assert_matches_fresh(e,chain,items)

    def test_dict_dst_fold_change_invalidates_source_fingerprint(self):
        from io import BytesIO
        from struct import pack
        from zoneinfo import ZoneInfo
        transition=int(datetime(2026,11,1,6,tzinfo=timezone.utc).timestamp())
        data=(b'TZif'+b'\x00'*16+pack('>6l',0,0,0,1,2,8)+pack('>l',transition)+b'\x01'
              +pack('>lbb',-14400,0,0)+pack('>lbb',-18000,0,4)+b'EDT\x00EST\x00')
        zone=ZoneInfo.from_file(BytesIO(data),key='test/source-fold')
        e,_,items=self.build(False)
        items[0].source.occurred_at=datetime(2026,11,1,4,tzinfo=timezone.utc)
        items[1].source.occurred_at=datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
        items[2].source.occurred_at=datetime(2026,11,1,6,tzinfo=timezone.utc)
        chain=EventChainIndex(e.backend,date_policy='source')
        self.assertEqual(chain.next_event_id(items[0].id),items[1].id)
        items[1].source.occurred_at=items[1].source.occurred_at.replace(fold=1)
        self.assertEqual(chain.next_event_id(items[0].id),items[2].id)
        self.assert_matches_fresh(e,chain,items)

if __name__=='__main__':unittest.main()
