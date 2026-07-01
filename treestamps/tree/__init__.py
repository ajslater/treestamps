"""Timestamp writer for keeping track of bulk optimizations."""

from treestamps.tree.set import TreestampsSet


class Treestamps(TreestampsSet):
    """
    Treestamps object to hold settings and caches.

    The linear inheritance chain (Init -> Wal -> Dump -> Get -> Load -> Set)
    exists only to split one class across files for readability; each layer
    is a facet of this single class, not a reusable mixin.
    """
