"""
CodeProvenance CLI
Command-line interface for codebase architectural drift auditing and refactoring.
"""

import sys
import io
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from codeprovenance.core.drift_tracker import DriftTracker
from codeprovenance.core.rules_engine import DEFAULT_BLUEPRINT

console = Console(force_terminal=True)


def show_banner():
    console.print(
        Panel.fit(
            "[bold cyan]🔍 CodeProvenance[/bold cyan] — [bold white]Codebase Architecture & Drift Detector[/bold white]\n"
            "[dim]Static AST Layer Compliance & Dependency Cycle Analyzer[/dim]",
            border_style="cyan"
        )
    )


def command_scan(args):
    show_banner()
    target_path = Path(args.path or ".").resolve()
    console.print(f"[bold cyan]Scanning directory:[/bold cyan] [yellow]{target_path}[/yellow]\n")

    tracker = DriftTracker()
    report = tracker.scan_project(target_path)

    # Health summary
    score_color = "green" if report.compliance_score_pct >= 85 else ("yellow" if report.compliance_score_pct >= 70 else "red")
    console.print(
        Panel(
            f"• [bold]Files Analyzed:[/bold] {report.total_files} files ({report.total_loc:,} lines of code)\n"
            f"• [bold]Architectural Compliance Score:[/bold] [{score_color} bold]{report.compliance_score_pct}%[/{score_color} bold]\n"
            f"• [bold]Status:[/bold] [{score_color}]{report.drift_status}[/{score_color}]\n"
            f"• [bold]Violations Detected:[/bold] [bold red]{len(report.violations)}[/bold red]",
            title="Audit Summary",
            border_style=score_color
        )
    )

    # Violations table
    if report.violations:
        table = Table(title="Architectural Boundary Violations", header_style="bold red")
        table.add_column("Severity", justify="center")
        table.add_column("Rule ID", style="dim")
        table.add_column("File / Module", style="bold yellow")
        table.add_column("Issue & Suggested Fix")

        for v in report.violations:
            sev_badge = f"[bold red]{v.severity.upper()}[/bold red]" if v.severity in ["critical", "high"] else f"[yellow]{v.severity.upper()}[/yellow]"
            table.add_row(
                sev_badge,
                v.rule_id,
                v.file_path,
                f"[bold]{v.title}[/bold]\n[dim]{v.description}[/dim]\n[green]Fix: {v.suggested_fix}[/green]"
            )
        console.print(table)
    else:
        console.print("\n[bold green]✔ No architectural violations detected! Codebase is in perfect compliance.[/bold green]\n")

    # Refactorings table
    if report.refactoring_recommendations:
        console.print("\n")
        ref_table = Table(title="Recommended Micro-Refactorings", header_style="bold cyan")
        ref_table.add_column("File", style="bold")
        ref_table.add_column("Action", style="white")
        ref_table.add_column("Est. Effort", justify="right", style="dim")

        for r in report.refactoring_recommendations[:5]:
            ref_table.add_row(
                r.file_path,
                f"{r.title}\n[dim]{r.suggested_diff}[/dim]",
                f"{r.estimated_effort_mins} mins"
            )
        console.print(ref_table)


def command_layers(args):
    show_banner()
    table = Table(title="Configured Architectural Layers", header_style="bold cyan")
    table.add_column("Layer Name", style="bold yellow")
    table.add_column("Matched Patterns")
    table.add_column("Allowed Dependencies", style="green")
    table.add_column("Role Description", style="dim")

    for l in DEFAULT_BLUEPRINT.layers:
        table.add_row(
            l.name,
            ", ".join(l.path_patterns),
            ", ".join(l.allowed_dependencies) if l.allowed_dependencies else "[dim]None (Base)[/dim]",
            l.description
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="CodeProvenance CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to run")

    scan_parser = subparsers.add_parser("scan", help="Scan a codebase directory for architectural drift")
    scan_parser.add_argument("path", nargs="?", default=".", help="Path to project directory")

    subparsers.add_parser("layers", help="View architectural layers and boundary rules")

    args = parser.parse_args()
    if args.subcommand == "scan":
        command_scan(args)
    elif args.subcommand == "layers":
        command_layers(args)
    else:
        show_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
