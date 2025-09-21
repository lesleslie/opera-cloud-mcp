"""
OPERA Cloud MCP Server CLI

Command-line interface for managing the OPERA Cloud MCP server.
"""

import os
import signal
import subprocess  # noqa: S404 - subprocess required for daemon management
import sys
import time
from pathlib import Path

import typer

from opera_cloud_mcp.server import app as mcp_app

# PID file location
PID_FILE = Path.home() / ".opera-cloud-mcp.pid"


def get_server_pid() -> int | None:
    """Get the PID of the running MCP server if it exists."""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())

        # Check if process is still running
        try:
            os.kill(pid, 0)  # Send null signal to check if process exists
            return pid
        except OSError:
            # Process doesn't exist, remove stale PID file
            PID_FILE.unlink(missing_ok=True)
            return None
    except (ValueError, FileNotFoundError):
        return None


def write_pid_file(pid: int) -> None:
    """Write the PID to the PID file."""
    PID_FILE.write_text(str(pid))


def remove_pid_file() -> None:
    """Remove the PID file."""
    PID_FILE.unlink(missing_ok=True)


def start_server(background: bool = False) -> None:
    """Start the OPERA Cloud MCP server."""
    existing_pid = get_server_pid()
    if existing_pid:
        typer.echo(f"MCP server is already running (PID: {existing_pid})")
        return

    if background:
        # Start the server in the background using subprocess
        typer.echo("Starting MCP server in background...")

        # Create a simple script to run the server
        server_script = f"""
import sys
import os
from opera_cloud_mcp.server import app as mcp_app

# Write PID to file
with open('{PID_FILE}', 'w') as f:
    f.write(str(os.getpid()))

try:
    mcp_app.run()
except Exception as e:
    sys.exit(1)
"""

        # Use subprocess to start the server in background
        # Safe subprocess usage: sys.executable is trusted, script is internal
        subprocess.Popen(  # noqa: S603 - Safe usage with trusted executable path
            [sys.executable, "-c", server_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Give it a moment to start and write PID
        time.sleep(2)

        # Check if PID file was created and process is running
        pid = get_server_pid()
        if pid:
            typer.echo(f"MCP server started successfully (PID: {pid})")
        else:
            typer.echo("Failed to start MCP server", err=True)
    else:
        # Start the server in foreground
        typer.echo("Starting MCP server...")
        write_pid_file(os.getpid())

        def signal_handler(signum: int, frame) -> None:
            typer.echo("\nShutting down MCP server...")
            remove_pid_file()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            mcp_app.run()
        finally:
            remove_pid_file()


def stop_server() -> None:
    """Stop the OPERA Cloud MCP server."""
    pid = get_server_pid()
    if not pid:
        typer.echo("MCP server is not running")
        return

    try:
        typer.echo(f"Stopping MCP server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        # Wait for the process to terminate
        for _ in range(10):  # Wait up to 10 seconds
            try:
                os.kill(pid, 0)
                time.sleep(1)
            except OSError:
                break
        else:
            # If still running after 10 seconds, force kill
            typer.echo("Force killing MCP server...")
            os.kill(pid, signal.SIGKILL)

        remove_pid_file()
        typer.echo("MCP server stopped successfully")

    except OSError as e:
        typer.echo(f"Error stopping MCP server: {e}", err=True)
        remove_pid_file()  # Clean up stale PID file


def restart_server() -> None:
    """Restart the OPERA Cloud MCP server."""
    pid = get_server_pid()
    if pid:
        typer.echo("Stopping existing MCP server...")
        stop_server()
        time.sleep(1)  # Give it a moment to fully stop

    typer.echo("Starting MCP server...")
    start_server(background=True)


def show_status() -> None:
    """Show the status of the OPERA Cloud MCP server."""
    pid = get_server_pid()
    if pid:
        typer.echo(f"MCP server is running (PID: {pid})")
    else:
        typer.echo("MCP server is not running")


def show_version() -> None:
    """Show version information."""
    typer.echo("OPERA Cloud MCP Server v0.1.0")


def main(
    start_mcp_server: bool = typer.Option(
        False, "--start-mcp-server", help="Start the OPERA Cloud MCP server"
    ),
    stop_mcp_server: bool = typer.Option(
        False, "--stop-mcp-server", help="Stop the OPERA Cloud MCP server"
    ),
    restart_mcp_server: bool = typer.Option(
        False, "--restart-mcp-server", help="Restart the OPERA Cloud MCP server"
    ),
    status: bool = typer.Option(
        False, "--status", help="Show the status of the OPERA Cloud MCP server"
    ),
    version: bool = typer.Option(False, "--version", help="Show version information"),
    background: bool = typer.Option(
        False,
        "--background",
        "-d",
        help="Run the server in the background (with --start-mcp-server)",
    ),
) -> None:
    """OPERA Cloud MCP Server management CLI."""

    # Count how many options were selected
    options_selected = sum(
        [start_mcp_server, stop_mcp_server, restart_mcp_server, status, version]
    )

    if options_selected == 0:
        typer.echo("OPERA Cloud MCP Server management CLI")
        typer.echo("Use --help to see available options")
        return

    if options_selected > 1:
        typer.echo("Error: Only one operation can be performed at a time")
        raise typer.Exit(1)

    if start_mcp_server:
        start_server(background)
    elif stop_mcp_server:
        stop_server()
    elif restart_mcp_server:
        restart_server()
    elif status:
        show_status()
    elif version:
        show_version()


if __name__ == "__main__":
    main()
