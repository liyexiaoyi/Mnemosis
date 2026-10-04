"""Source-aware time selection must not confuse frequency, import time, or ambiguity with event time."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import inspect
import json
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.schema import EventChainIndex
from mnemosis.types import MemoryKind, SourceRecord, SourceType

NOW=datetime(2026,10,4,12,tzinfo=timezone.utc)
OLD='2026-01-01T10:00:00+00:00'
NEW='2026-09-01T10:00:00+00:00'
QUERY='上次私教课练了什么？'

class SourceTemporalTests(unittest.TestCase):
    def engine(self,disk=False):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        engine=MemoryEngine(str(Path(folder.name)/'memory.db') if disk else None,auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def item(self,engine,text,stamp=None,evidence=1,kind=MemoryKind.EPISODIC,cues=None):
        return engine.remember(text,kind=kind,source=SourceRecord(SourceType.USER,
            occurred_at=datetime.fromisoformat(stamp) if stamp else None),
            cues=cues or ['小林','session1'],evidence_count=evidence,created_at=NOW,
            auto_cues=False,auto_context=False)

    def state(self,e):
        return json.dumps(dict(items=[i.to_dict() for i in e.store.all_active()],
            links=sorted(e.backend.all_links()),log=e.get_recall_log()),sort_keys=True)

    def recall(self,e,query=QUERY,**kw):
        # Run the first test against the old public behavior as well; this
        # turns the pre-change failure into the actual wrong selection.
        if 'temporal_policy' in inspect.signature(e.recall).parameters:
            kw.setdefault('temporal_policy','source')
        kw.setdefault('now',NOW);kw.setdefault('read_only',True)
        return e.recall(query,**kw)

    def test_public_latest_uses_source_time_on_both_backends(self):
        for disk in (False,True):
            e=self.engine(disk)
            self.item(e,'私教课练腿。',OLD,evidence=20)
            latest=self.item(e,'私教课练胸。',NEW)
            before=self.state(e)
            for k in (1,2,5):
                with self.subTest(disk=disk,top_k=k):
                    result=self.recall(e,top_k=k)
                    self.assertEqual(result[0].item.id,latest.id)
                    self.assertTrue(any('来源发生时间' in reason for reason in result[0].reasons))
            self.assertEqual(self.state(e),before)

    def test_first_and_next_use_source_time(self):
        for query,old,new in [('第一次私教课练了什么？',NEW,OLD),
            ('下次私教课练什么？',OLD,'2026-11-01T10:00:00+00:00')]:
            e=self.engine()
            distractor=self.item(e,'私教课练腿。',old,evidence=20)
            target=self.item(e,'私教课练胸。',new)
            result=self.recall(e,query,top_k=5)
            self.assertEqual(result[0].item.id,target.id)
            if '下次' in query: self.assertNotIn(distractor.id,[r.item.id for r in result])

    def test_exact_chinese_and_iso_date(self):
        e=self.engine()
        self.item(e,'私教课练腿。',NEW,evidence=20)
        target=self.item(e,'私教课练胸。',OLD)
        for query in ('2026年1月1日私教课练了什么？','2026-01-01 私教课练了什么？'):
            self.assertEqual(self.recall(e,query,top_k=1)[0].item.id,target.id)

    def test_same_day_source_instants_order_past_and_future(self):
        e=self.engine()
        self.item(e,'私教课练腿。','2026-10-04T08:00:00+00:00',evidence=20)
        last=self.item(e,'私教课练胸。','2026-10-04T10:00:00+00:00')
        next_item=self.item(e,'私教课练背。','2026-10-04T15:00:00+00:00')
        self.assertEqual(self.recall(e,top_k=1)[0].item.id,last.id)
        self.assertEqual(self.recall(e,'下次私教课练什么？',top_k=1)[0].item.id,next_item.id)

    def test_offset_is_normalized_before_direction_and_exact_date(self):
        e=self.engine()
        past=self.item(e,'私教课练腿。','2026-10-05T00:30:00+14:00',evidence=20)
        future=self.item(e,'私教课练胸。','2026-10-04T15:00:00+00:00')
        self.assertEqual(self.recall(e,'下次私教课练什么？',top_k=1)[0].item.id,future.id)
        self.assertEqual(self.recall(e,top_k=1)[0].item.id,past.id)
        self.assertEqual(self.recall(e,'2026年10月4日私教课练了什么？',top_k=1)[0].item.id,past.id)

    def test_query_timezone_controls_calendar_date(self):
        e=self.engine()
        target=self.item(e,'私教课练腿。','2026-10-03T23:00:00+00:00',evidence=20)
        self.item(e,'私教课练胸。',OLD)
        clock=datetime(2026,10,4,12,tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(self.recall(e,'2026年10月4日私教课练了什么？',now=clock,top_k=1)[0].item.id,target.id)

    def test_unknown_conflict_invalid_naive_and_multiple_dates_are_uncertain(self):
        cases=[('私教课练腿。',None),('私教课练腿。','2026-09-01T10:00:00'),
            ('2026年9月1日私教课练腿。',OLD),('2026年2月30日私教课练腿。',NEW),
            ('2026年1月1日私教课练腿，2026年9月1日练胸。',NEW),
            ('私教课练腿，生日是2026年9月1日。',NEW)]
        for text,stamp in cases:
            with self.subTest(text=text,stamp=stamp):
                e=self.engine();self.item(e,text,stamp)
                result=self.recall(e,top_k=1)
                self.assertTrue(result)
                self.assertFalse(result[0].confident)
                self.assertFalse(any(r.startswith('时间锚点') for r in result[0].reasons))

    def test_semantic_source_does_not_claim_current_validity(self):
        e=self.engine()
        self.item(e,'小林住在北京。',OLD,evidence=20,kind=MemoryKind.SEMANTIC)
        self.item(e,'小林住在上海。',NEW,kind=MemoryKind.SEMANTIC)
        result=self.recall(e,'现在小林住在哪里？',top_k=1)
        self.assertFalse(result[0].confident)
        self.assertFalse(any(r.startswith('时间锚点') for r in result[0].reasons))

    def test_yearless_date_requires_source_agreement(self):
        e=self.engine()
        self.item(e,'1月1日私教课练腿。',OLD,evidence=20)
        target=self.item(e,'9月1日私教课练胸。',NEW)
        self.assertEqual(self.recall(e,top_k=1)[0].item.id,target.id)
        e=self.engine();self.item(e,'8月1日私教课练腿。',NEW)
        self.assertFalse(self.recall(e,top_k=1)[0].confident)

    def test_cue_date_conflict_is_not_silently_overridden(self):
        e=self.engine();self.item(e,'私教课练腿。',NEW,cues=['2026-01-01','私教课'])
        self.assertFalse(self.recall(e,top_k=1)[0].confident)

    def test_content_dates_still_work_without_source(self):
        for disk in (False,True):
            e=self.engine(disk)
            self.item(e,'2026 年 1 月 1 日私教课练腿。',evidence=20)
            target=self.item(e,'2026 年 9 月 1 日私教课练胸。')
            self.assertEqual(self.recall(e,top_k=1)[0].item.id,target.id)

    def test_filters_and_topic_relevance_still_apply(self):
        e=self.engine()
        old=self.item(e,'私教课练腿。',OLD)
        blocked=self.item(e,'私教课练胸。',NEW)
        self.item(e,'篮球课练投篮。','2026-10-01T10:00:00+00:00',evidence=20)
        self.assertEqual(self.recall(e,top_k=1,exclude_ids={blocked.id})[0].item.id,old.id)
        e.forget(blocked.id)
        self.assertEqual(self.recall(e,top_k=1)[0].item.id,old.id)

    def test_default_legacy_keeps_old_selection(self):
        e=self.engine();old=self.item(e,'私教课练腿。',OLD,evidence=20)
        self.item(e,'私教课练胸。',NEW)
        result=e.recall(QUERY,top_k=1,now=NOW,read_only=True)
        self.assertEqual(result[0].item.id,old.id)

    def test_plain_query_has_no_new_time_claim(self):
        e=self.engine();self.item(e,'私教课练腿。')
        result=self.recall(e,'私教课内容',top_k=1)
        self.assertFalse(any('时间' in reason for reason in result[0].reasons))

    def test_invalid_policy_and_naive_clock_fail_before_learning(self):
        e=self.engine();self.item(e,'私教课练腿。',OLD)
        before=self.state(e)
        for policy in ('oops',None,[]):
            with self.assertRaises(ValueError): e.recall(QUERY,temporal_policy=policy)
        with self.assertRaises(ValueError): e.recall(QUERY,temporal_policy='source',now=datetime(2026,10,4))
        self.assertEqual(self.state(e),before)

    def test_source_chain_uses_shared_dates_and_actual_instant_order(self):
        for disk in (False,True):
            e=self.engine(disk)
            a=self.item(e,'visited aquarium','2026-10-04T08:00:00+00:00')
            c=self.item(e,'ate dinner','2026-10-04T10:00:00+00:00')
            b=self.item(e,'took a walk','2026-10-04T09:00:00+00:00')
            chain=EventChainIndex(e.backend,date_policy='source')
            self.assertEqual(chain.next_event_id(a.id),b.id)
            self.assertEqual(chain.next_event_id(b.id),c.id)
            self.assertIsNone(e.event_chain.next_event_id(a.id))
            changed=e.backend.get(b.id)
            changed.source.occurred_at=datetime.fromisoformat('2026-10-04T11:00:00+00:00')
            e.backend.update(changed)
            self.assertEqual(chain.next_event_id(a.id),c.id)

    def test_source_chain_omits_ambiguous_event(self):
        e=self.engine();a=self.item(e,'visited aquarium',OLD)
        self.item(e,'2026年9月1日 had lunch',OLD)
        c=self.item(e,'ate dinner',NEW)
        chain=EventChainIndex(e.backend,date_policy='source')
        self.assertEqual(chain.next_event_id(a.id),c.id)

    def test_source_chain_is_used_by_public_recall(self):
        e=self.engine();self.item(e,'anchorneedle aquarium',OLD)
        target=self.item(e,'destination tacos',NEW)
        result=self.recall(e,'anchorneedle aquarium',top_k=5,pattern_completion=False,concept_coverage=False)
        self.assertTrue(any(r.item.id==target.id and any('时序后继' in why for why in r.reasons) for r in result))

    def test_final_learning_targets_selected_event_only(self):
        e=self.engine(True);old=self.item(e,'私教课练腿。',OLD,evidence=20)
        target=self.item(e,'私教课练胸。',NEW)
        self.recall(e,top_k=1,read_only=False,learning_policy='final')
        self.assertEqual(e.backend.get(old.id).access_count,0)
        selected=e.backend.get(target.id)
        self.assertEqual(selected.access_count,1)
        self.assertEqual(selected.verified_successes,0)
        self.assertEqual(selected.evidence_count,1)

    def test_diagnostic_and_mcp_expose_date_basis_and_uncertainty(self):
        e=self.engine();target=self.item(e,'私教课练胸。',NEW)
        before=self.state(e)
        diagnostic=e.temporal_anchor(QUERY,now=NOW,temporal_policy='source')
        self.assertEqual(diagnostic['anchored'][0]['id'],target.id)
        self.assertEqual(self.state(e),before)
        server=MCPServer(engine=e)
        rows=server._call_tool('recall',dict(query=QUERY,read_only=True,temporal_policy='source'))
        self.assertIn('confident',rows[0]);self.assertIn('reasons',rows[0])
        self.assertTrue(any('来源发生时间' in why for why in rows[0]['reasons']))

    def test_next_with_only_expired_events_does_not_claim_certainty(self):
        e=self.engine();self.item(e,'私教课练腿。',OLD)
        result=self.recall(e,'下次私教课练什么？',top_k=1)
        self.assertTrue(not result or not result[0].confident)
        self.assertFalse(any(why.startswith('时间锚点') for r in result for why in r.reasons))

    def test_exact_date_without_match_does_not_claim_certainty(self):
        e=self.engine();self.item(e,'私教课练腿。',OLD)
        for query in ('2026年8月1日私教课练了什么？','2026年2月30日私教课练了什么？'):
            result=self.recall(e,query,top_k=1)
            self.assertTrue(not result or not result[0].confident)

    def test_dst_fold_uses_real_instant_instead_of_wall_clock(self):
        # Real stdlib ZoneInfo with one controlled TZif transition; no OS
        # timezone database dependency and no mocked datetime behavior.
        from io import BytesIO
        from struct import pack
        from zoneinfo import ZoneInfo
        transition=int(datetime(2026,11,1,6,tzinfo=timezone.utc).timestamp())
        data=(b'TZif'+b'\x00'*16+pack('>6l',0,0,0,1,2,8)+pack('>l',transition)+b'\x01'
              +pack('>lbb',-14400,0,0)+pack('>lbb',-18000,0,4)+b'EDT\x00EST\x00')
        zone=ZoneInfo.from_file(BytesIO(data),key='test/fall-back')
        clock=datetime(2026,11,1,6,15,tzinfo=timezone.utc).astimezone(zone)
        e=self.engine();self.item(e,'私教课练腿。','2026-11-01T04:00:00+00:00',evidence=20)
        target=self.item(e,'私教课练胸。','2026-11-01T05:30:00+00:00')
        self.assertEqual(self.recall(e,now=clock,top_k=1)[0].item.id,target.id)

    def test_mcp_time_diagnostic_forwards_source_policy(self):
        e=self.engine();target=self.item(e,'私教课练胸。',OLD)
        server=MCPServer(engine=e)
        before=self.state(e)
        result=server._call_tool('temporal_anchor',dict(query=QUERY,temporal_policy='source'))
        self.assertTrue(result['anchored'], 'MCP lost the requested source-time strategy')
        self.assertEqual(result['anchored'][0]['id'],target.id)
        self.assertEqual(self.state(e),before)

if __name__=='__main__': unittest.main()
