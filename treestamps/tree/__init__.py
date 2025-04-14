"""Timestamp writer for keeping track of bulk optimizations."""

from treestamps.tree.dump import TreestampsDump
from treestamps.tree.load import TreestampLoad
from treestamps.tree.set import TreestampsSet


class Treestamps(TreestampsSet, TreestampLoad, TreestampsDump):
    """Treestamps object to hold settings and caches."""
