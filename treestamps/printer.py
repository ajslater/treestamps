"""Print Messages."""

from termcolor import cprint


class Printer:
    """Printing messages."""

    def __init__(self, verbose: int):
        """Initialize verbosity and flags."""
        self._verbose = verbose
        self._after_newline = True

    def _message(
        self, reason, color="white", attrs=None, *, force_verbose=False, end="\n"
    ):
        """Print a dot or skip message."""
        if self._verbose < 1:
            return
        if (self._verbose == 1 and not force_verbose) or not reason:
            cprint(".", color, attrs=attrs, end="", flush=True)
            self._after_newline = False
            return
        if not self._after_newline:
            reason = "\n" + reason
        attrs = attrs if attrs else []
        cprint(reason, color, attrs=attrs, end=end, flush=True)
        if end:
            self._after_newline = True

    def skip(self, message, path):
        """Skip Message."""
        parts = ["Skip", message, str(path)]
        message = ": ".join(parts)
        self._message(message, color="dark_grey")

    def load(self, message, path):
        """Save timestamps."""
        message = f"{message} {path}"
        self._message(message, color="cyan")

    def save(self, message, path):
        """Save timestamps."""
        message = f"{message} {path}"
        self._message(message, color="green", attrs=["bold"])

    def compact(self, message, path, timestamp):
        """Compact timestamps."""
        message = ": ".join((message, str(path), str(timestamp)))
        self._message(message, color="dark_grey", attrs=["dark"])

    def warn(self, message: str, exc: Exception | None = None):
        """Warning."""
        message = "WARNING: " + message
        if exc:
            message += f": {exc}"
        self._after_newline = False
        self._message(message, color="light_yellow", force_verbose=True)

    def error(self, message: str, exc: Exception | None = None):
        """Error."""
        message = "ERROR: " + message
        if exc:
            message += f": {exc}"
        self._message(message, color="light_red", force_verbose=True)
