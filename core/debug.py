from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    _console: Optional[Console] = Console()
except Exception:
    _console = None
    Panel = None  # type: ignore


def debug_log(enabled: bool, title: str, body: str) -> None:
    if not enabled:
        return
    if _console and Panel:
        _console.print(Panel.fit(body, title=title))
    else:
        print(f"=== {title} ===\n{body}\n=== end {title} ===")
