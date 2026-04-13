"""Treestamps base class with shared filename utilities."""

from pathlib import Path


class TreestampsBase:
    """Shared base for Treestamps and Grovestamps."""

    _FILENAME_TEMPLATE: str = ".{program_name}_treestamps.yaml"
    _WAL_FILENAME_TEMPLATE: str = ".{program_name}_treestamps.wal.yaml"

    @staticmethod
    def get_dir(path: Path | str) -> Path:
        """Return a directory for a path."""
        path = Path(path)
        return path if path.is_dir() else path.parent

    @classmethod
    def get_filename(cls, program_name: str) -> str:
        """Return the timestamps filename for a program."""
        return cls._FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def get_wal_filename(cls, program_name: str) -> str:
        """Return the write ahead log filename for the program."""
        return cls._WAL_FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def get_filenames(cls, program_name: str) -> tuple[str, str]:
        """Get all filenames produced by treestamps."""
        return (cls.get_filename(program_name), cls.get_wal_filename(program_name))
