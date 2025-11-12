#!/usr/bin/env python3
"""
Lazy_Bird CLI - Main command-line interface

Provides the main entry point for the lazy-bird command.
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional

from lazy_bird import __version__, PACKAGE_ROOT


def print_banner():
    """Print the Lazy_Bird ASCII banner"""
    banner = r"""
    🦜                                                      🦜
       _           _     ________  __     __
      | |         / \    |___  /   \ \   / /
      | |        / _ \      / /     \ \_/ /
      | |___    / ___ \    / /__     \   /
      |_____|  /_/   \_\  /_____|     |_|

       ____    ___   ____    ____
      | __ )  |_ _| |  _ \  |  _ \
      |  _ \   | |  | |_) | | | | |
      | |_) |  | |  |  _ <  | |_| |
      |____/  |___| |_| \_\ |____/
    💤                                                      💤

    Version: {version}
    Automate ANY development project while you sleep 🦜💤
    """.format(version=__version__)
    print(banner)


def run_wizard(args: List[str]) -> int:
    """Run the setup wizard"""
    wizard_script = PACKAGE_ROOT / "wizard.sh"
    if not wizard_script.exists():
        print(f"Error: Wizard script not found at {wizard_script}")
        return 1

    cmd = ["bash", str(wizard_script)] + args
    return subprocess.call(cmd)


def run_server(port: int = 5000, host: str = "127.0.0.1") -> int:
    """Run the web backend server"""
    try:
        # Import here to avoid import errors if Flask is not installed
        sys.path.insert(0, str(PACKAGE_ROOT / "web" / "backend"))
        from app import app

        print(f"🚀 Starting Lazy_Bird web server on http://{host}:{port}")
        print(f"📊 Dashboard: http://{host}:{port}")
        print(f"📡 API: http://{host}:{port}/api")
        print()

        app.run(host=host, port=port, debug=False)
        return 0
    except ImportError as e:
        print(f"Error: Failed to import Flask application: {e}")
        print("Install web dependencies: pip install lazy-bird[web]")
        return 1
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1


def run_godot_server(args: List[str]) -> int:
    """Run the Godot test server"""
    script = PACKAGE_ROOT / "scripts" / "godot-server.py"
    if not script.exists():
        print(f"Error: Godot server script not found at {script}")
        return 1

    cmd = [sys.executable, str(script)] + args
    return subprocess.call(cmd)


def run_issue_watcher(args: List[str]) -> int:
    """Run the issue watcher"""
    script = PACKAGE_ROOT / "scripts" / "issue-watcher.py"
    if not script.exists():
        print(f"Error: Issue watcher script not found at {script}")
        return 1

    cmd = [sys.executable, str(script)] + args
    return subprocess.call(cmd)


def run_project_manager(args: List[str]) -> int:
    """Run the project manager"""
    script = PACKAGE_ROOT / "scripts" / "project-manager.py"
    if not script.exists():
        print(f"Error: Project manager script not found at {script}")
        return 1

    cmd = [sys.executable, str(script)] + args
    return subprocess.call(cmd)


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point"""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="lazy-bird",
        description="Automate development projects with Claude Code",
        epilog="For more information, visit: https://github.com/yusufkaraaslan/lazy-bird"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"lazy-bird {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup wizard
    wizard_parser = subparsers.add_parser(
        "setup",
        help="Run the setup wizard"
    )
    wizard_parser.add_argument(
        "wizard_args",
        nargs="*",
        help="Arguments to pass to the wizard"
    )

    # Web server
    server_parser = subparsers.add_parser(
        "server",
        help="Start the web backend server"
    )
    server_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)"
    )

    # Godot server
    godot_parser = subparsers.add_parser(
        "godot",
        help="Run the Godot test server"
    )
    godot_parser.add_argument(
        "godot_args",
        nargs="*",
        help="Arguments to pass to Godot server"
    )

    # Issue watcher
    watcher_parser = subparsers.add_parser(
        "watch",
        help="Run the issue watcher"
    )
    watcher_parser.add_argument(
        "watcher_args",
        nargs="*",
        help="Arguments to pass to issue watcher"
    )

    # Project manager
    project_parser = subparsers.add_parser(
        "project",
        help="Manage projects"
    )
    project_parser.add_argument(
        "project_args",
        nargs="*",
        help="Arguments to pass to project manager"
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show system status"
    )

    # Parse arguments
    args = parser.parse_args(argv)

    # Show banner for main command
    if not args.command or args.command == "status":
        print_banner()

    # Execute command
    if not args.command:
        parser.print_help()
        return 0

    elif args.command == "setup":
        return run_wizard(args.wizard_args)

    elif args.command == "server":
        return run_server(port=args.port, host=args.host)

    elif args.command == "godot":
        return run_godot_server(args.godot_args)

    elif args.command == "watch":
        return run_issue_watcher(args.watcher_args)

    elif args.command == "project":
        return run_project_manager(args.project_args)

    elif args.command == "status":
        # Run wizard status
        return run_wizard(["--status"])

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
