"""Print Messages."""

from pathlib import Path

from termcolor import cprint


class Printer:
    """Printing messages."""

    def __init__(self, verbose: int) -> None:
        """Initialize verbosity and flags."""
        self._verbose: int = verbose
        self._after_newline: bool = True

    def _message(
        self,
        reason: str,
        color: str = "white",
        attrs: list[str] | None = None,
        *,
        force_verbose: bool = False,
        end: str = "\n",
    ) -> None:
        """Print a dot or skip message."""
        if self._verbose < 1:
            return
        if (self._verbose == 1 and not force_verbose) or not reason:
            cprint(".", color, attrs=attrs, end="", flush=True)
            self._after_newline = False
            return
        if not self._after_newline:
            reason = "\n" + reason
        attrs = attrs or []
        cprint(reason, color, attrs=attrs, end=end, flush=True)
        if end:
            self._after_newline = True

    def skip(self, message: str, path: Path) -> None:
        """Skip Message."""
        parts = ["Skip", message, str(path)]
        message = ": ".join(parts)
        self._message(message, color="dark_grey")

    def load(self, message: str, path: Path) -> None:
        """Save timestamps."""
        message = f"{message} {path}"
        self._message(message, color="cyan")

    def save(self, message: str, path: Path) -> None:
        """Save timestamps."""
        message = f"{message} {path}"
        self._message(message, color="green", attrs=["bold"])

    def compact(self, message: str, path: Path, timestamp: float) -> None:
        """Compact timestamps."""
        message = ": ".join((message, str(path), str(timestamp)))
        self._message(message, color="dark_grey", attrs=["dark"])

    def warn(self, message: str, exc: Exception | None = None) -> None:
        """Warning."""
        message = "WARNING: " + message
        if exc:
            message += f": {exc}"
        self._after_newline = False
        self._message(message, color="light_yellow", force_verbose=True)

    def error(self, message: str, exc: Exception | None = None) -> None:
        """Error."""
        message = "ERROR: " + message
        if exc:
            message += f": {exc}"
        self._message(message, color="light_red", force_verbose=True)
