"""
main.py — CLI entry point for the Production Incident Investigator RAG.

Usage:
  
  pythonpython main.py --ingest main.py --ingest --reset
  python main.py --query "payment service 500 errors after 2pm deploy"
  python main.py --stats
"""
import sys
import json
import io
from pathlib import Path

# Ensure UTF-8 output on Windows (emoji support)
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent))

from src.investigator import Investigator
from config import SOURCE_ICONS

app = typer.Typer(
    name="incident-investigator",
    help="🔍 Production Incident Investigator RAG — powered by Gemini",
    add_completion=False,
)
console = Console()


@app.command()
def ingest(
    reset: bool = typer.Option(False, "--reset", help="Wipe and re-index the vector store"),
):
    """Ingest all 7 data sources into the vector store."""
    console.rule("[bold cyan]📥 Ingesting Sources")
    investigator = Investigator()

    if reset:
        console.print("[yellow]⚠️  Resetting vector store before ingestion...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Ingesting and embedding all sources...", total=None)
        total = investigator.ingest_all(verbose=True, reset=reset)
        progress.update(task, completed=True)

    stats = investigator.store_stats()
    table = Table(title="Vector Store Contents", show_header=True)
    table.add_column("Source", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    for source, count in stats["sources"].items():
        icon = SOURCE_ICONS.get(source, "•")
        table.add_row(f"{icon} {source}", str(count))
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{stats['total_chunks']}[/bold]")
    console.print(table)


@app.command()
def query(
    question: str = typer.Argument(..., help="Incident description or query"),
    sources: str = typer.Option(None, "--sources", help="Comma-separated source names to enable"),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON instead of formatted report"),
    save: Path = typer.Option(None, "--save", help="Save report to a JSON file"),
):
    """Investigate an incident by natural language query."""
    enabled = [s.strip() for s in sources.split(",")] if sources else None
    investigator = Investigator(enabled_sources=enabled)

    if not investigator.is_indexed():
        console.print(
            Panel(
                "[red]Vector store is empty![/red]\n"
                "Run [bold cyan]python main.py ingest[/bold cyan] first.",
                title="⚠️  Not Indexed",
            )
        )
        raise typer.Exit(1)

    console.rule(f"[bold cyan]🔍 Investigating: {question}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        t1 = progress.add_task("Retrieving relevant chunks...", total=None)
        # Run the investigation
        report, meta = investigator.investigate(question, verbose=False)
        progress.update(t1, completed=True)

    if output_json:
        console.print_json(report.model_dump_json(indent=2))
    else:
        # Display formatted markdown report
        console.print()
        console.print(Markdown(report.to_markdown()))
        console.print()
        _print_pipeline_meta(meta, console)

    if save:
        save.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n💾 Report saved to [cyan]{save}[/cyan]")


@app.command()
def stats():
    """Show vector store statistics."""
    investigator = Investigator()
    s = investigator.store_stats()

    if s["total_chunks"] == 0:
        console.print("[yellow]Vector store is empty. Run 'python main.py ingest' first.")
        return

    table = Table(title="📊 Vector Store Statistics")
    table.add_column("Source", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    for source, count in s["sources"].items():
        icon = SOURCE_ICONS.get(source, "•")
        table.add_row(f"{icon} {source}", str(count))
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{s['total_chunks']}[/bold]")
    console.print(table)


def _print_pipeline_meta(meta: dict, console: Console) -> None:
    table = Table(title="Pipeline Metadata", show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value", style="white")
    table.add_row("Candidates retrieved", str(meta.get("candidates_count", "?")))
    table.add_row("After reranking", str(meta.get("ranked_count", "?")))
    table.add_row("Sources in context", ", ".join(meta.get("sources_in_context", [])))
    table.add_row("Severity", meta.get("report_severity", "?"))
    table.add_row("Confidence", meta.get("report_confidence", "?"))
    console.print(table)


if __name__ == "__main__":
    app()
