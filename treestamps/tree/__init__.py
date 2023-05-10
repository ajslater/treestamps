"""Timestamp writer for keeping track of bulk optimizations."""
from treestamps.tree.dump import DumpMixin
from treestamps.tree.load import LoadMixin
from treestamps.tree.set import SetMixin


class Treestamps(SetMixin, LoadMixin, DumpMixin):
    """Treestamps object to hold settings and caches."""
