from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

def get_console():
    """Return a shared rich Console instance."""
    return Console()

def get_progress(console=None, total=100, description="Processing..."):
    """Return a standardized Progress instance."""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console or get_console(),
    ) 