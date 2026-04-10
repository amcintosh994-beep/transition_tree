from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from mttt.context.events import (
    append_context_item_archived_event,
    append_context_item_set_event,
)
from mttt.context.model import ContextItem
from mttt.context.replay import replay_context


class TestContextReplay(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.data_dir = self.tmpdir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_context_set_update_archive_replay(self) -> None:
        append_context_item_set_event(
            self.data_dir,
            item=ContextItem(
                item_id="ctx_0001",
                category="current_state",
                key="hrt_active",
                value=True,
                confidence="self_reported",
                source="test",
            ),
            ts=1,
        )

        append_context_item_set_event(
            self.data_dir,
            item=ContextItem(
                item_id="ctx_0002",
                category="current_state",
                key="estradiol_mg_per_day",
                value=6.0,
                confidence="self_reported",
                source="test",
            ),
            ts=2,
        )

        append_context_item_set_event(
            self.data_dir,
            item=ContextItem(
                item_id="ctx_0003",
                category="current_state",
                key="estradiol_mg_per_day",
                value=8.0,
                confidence="self_reported",
                source="test",
            ),
            ts=3,
        )

        append_context_item_archived_event(
            self.data_dir,
            category="current_state",
            key="hrt_active",
            ts=4,
        )

        replayed = replay_context(self.data_dir)

        self.assertIsNone(replayed.get("current_state", "hrt_active"))
        self.assertIsNotNone(replayed.get("current_state", "estradiol_mg_per_day"))
        self.assertEqual(
            replayed.get("current_state", "estradiol_mg_per_day").value,
            8.0,
        )

