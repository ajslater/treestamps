"""WAL entries must survive dumps()/dump_dict() without a snapshot."""

import pytest

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests-wal-persistence"
FIRST_TS = 100.0
SECOND_TS = 150.0


class TestWalPersistence(BaseTestDir):
    """dumps() and dump_dict() are pure serialization; they must not damage the WAL."""

    @pytest.mark.xfail(
        strict=True,
        reason="dump_dict() closes the WAL so the next set() truncates it on disk",
    )
    def test_wal_survives_dumps(self) -> None:
        """Entries WAL'd before a dumps() call must survive a crash after it."""
        config = GrovestampsConfig(PROGRAM_NAME, paths=(self.tmp_root,))
        gs = Grovestamps(config)
        ts = gs[self.tmp_root]
        assert ts.set(self.tmp_root / "first", FIRST_TS) == FIRST_TS

        # Serialize to string only — must not touch the on-disk WAL.
        assert ts.dumps()

        assert ts.set(self.tmp_root / "second", SECOND_TS) == SECOND_TS
        if ts._wal:
            ts._wal.flush()

        # Simulate a crash: no dumpf(). Reload from the WAL alone.
        gs2 = Grovestamps(config)
        ts2 = gs2[self.tmp_root]
        assert ts2.get(self.tmp_root / "second") == SECOND_TS
        assert ts2.get(self.tmp_root / "first") == FIRST_TS
