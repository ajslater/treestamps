"""Loading a parent yaml with an above-root entry must not crash on dump."""

from pathlib import Path

from ruamel.yaml import YAML

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests-parent-load"
TS_FN = f".{PROGRAM_NAME}_treestamps.yaml"


class TestParentLoad(BaseTestDir):
    """Loading parent timestamps that point at the parent itself."""

    @staticmethod
    def _write_parent_yaml(parent_dir: Path, abs_path_key: str, ts: float) -> None:
        """Write a treestamps yaml at ``parent_dir`` with an above-root entry."""
        yaml_obj = YAML()
        ts_config = {"ignore": frozenset(), "symlinks": True}
        yaml = {
            "config": {},
            "treestamps_config": ts_config,
            abs_path_key: ts,
        }
        # Custom representer for frozenset (matches treestamps's own dump).
        from ruamel.yaml import SafeRepresenter

        yaml_obj.representer.add_representer(
            frozenset, SafeRepresenter.represent_set
        )
        yaml_obj.dump(yaml, parent_dir / TS_FN)

    def test_parent_yaml_entry_above_root_dumpf(self) -> None:
        """
        Parent-yaml above-root entry must not crash dumpf.

        A parent yaml whose only entry is the parent dir itself must not
        crash ``dumpf`` on a child-rooted Grovestamps.

        Regression: v4.0.0/4.0.1 stored the above-root entry under its
        absolute path, then ``_serialize_timestamps`` called
        ``abs_path.relative_to(self.root_dir)`` and raised ``ValueError``
        because the entry was outside the tree.
        """
        child_dir = self.TMP_ROOT / "child"
        child_dir.mkdir()

        # Parent yaml lists the parent dir itself as the only entry.
        ts = 1_700_000_000.0
        self._write_parent_yaml(self.TMP_ROOT, str(self.TMP_ROOT), ts)

        config = GrovestampsConfig(
            program_name=PROGRAM_NAME,
            paths=(child_dir,),
            verbose=0,
            check_config=False,
        )
        gs = Grovestamps(config)

        # Lookup for any path under the child should inherit the parent ts.
        loaded = gs[child_dir].get(child_dir / "anything.txt")
        assert loaded == ts

        # The crash this test exists to prevent.
        gs.dumpf()

        # Child yaml should now exist with a single root-relative entry.
        child_yaml = child_dir / TS_FN
        assert child_yaml.exists()
