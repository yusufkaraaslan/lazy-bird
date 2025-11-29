#!/usr/bin/env python3
"""
Lazy_Bird Project Manager CLI
Manage multiple projects in Phase 1.1 multi-project configuration
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import json


def load_config(config_path: Path) -> Dict:
    """Load configuration from YAML file"""
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import yaml

        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        print("Error: PyYAML not installed. Install with: pip3 install pyyaml", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)


def save_config(config_path: Path, config: Dict):
    """Save configuration to YAML file"""
    try:
        import yaml

        # Backup existing config
        if config_path.exists():
            backup_path = config_path.with_suffix(".yml.backup")
            config_path.rename(backup_path)
            print(f"✅ Backup created: {backup_path}")

        with open(config_path, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Configuration saved: {config_path}")
    except Exception as e:
        print(f"Error saving configuration: {e}", file=sys.stderr)
        sys.exit(1)


def get_projects(config: Dict) -> List[Dict]:
    """Get projects list from config"""
    if "projects" in config and config["projects"]:
        return config["projects"]
    return []


def find_project(projects: List[Dict], project_id: str) -> Optional[Dict]:
    """Find project by ID"""
    for project in projects:
        if project.get("id") == project_id:
            return project
    return None


def validate_project(project: Dict, allow_partial: bool = False) -> List[str]:
    """Validate project fields, return list of errors"""
    required_fields = ["id", "name", "type", "path", "repository", "git_platform", "test_command"]
    errors = []

    if not allow_partial:
        for field in required_fields:
            if field not in project or not project[field]:
                errors.append(f"Missing required field: {field}")

    # Validate field formats
    if "id" in project:
        project_id = project["id"]
        if not project_id or not project_id.replace("-", "").replace("_", "").isalnum():
            errors.append(
                f"Invalid project ID: '{project_id}' (must be alphanumeric with dashes/underscores)"
            )

    if "git_platform" in project and project["git_platform"] not in ["github", "gitlab"]:
        errors.append(
            f"Invalid git_platform: '{project['git_platform']}' (must be 'github' or 'gitlab')"
        )

    if "path" in project:
        project_path = Path(project["path"])
        if not project_path.exists():
            errors.append(f"Project path does not exist: {project['path']}")
        elif not project_path.is_dir():
            errors.append(f"Project path is not a directory: {project['path']}")

    return errors


def cmd_list(args):
    """List all projects"""
    config = load_config(args.config)
    projects = get_projects(config)

    if not projects:
        print("No projects configured.")
        print("")
        print("Add a project with:")
        print(
            f'  {sys.argv[0]} add --id my-project --name "My Project" --type godot --path /path/to/project ...'
        )
        return

    print(f"\n{'='*80}")
    print(f"Lazy_Bird Projects ({len(projects)} total)")
    print(f"{'='*80}\n")

    for i, project in enumerate(projects, 1):
        enabled = project.get("enabled", True)
        status = "✅ ENABLED" if enabled else "❌ DISABLED"

        print(
            f"{i}. [{project.get('id', 'unknown')}] {project.get('name', 'Unnamed')} ({project.get('type', 'unknown')})"
        )
        print(f"   Status: {status}")
        print(f"   Path: {project.get('path', 'N/A')}")
        print(f"   Repository: {project.get('repository', 'N/A')}")
        print(f"   Platform: {project.get('git_platform', 'N/A')}")
        print(f"   Test: {project.get('test_command', 'N/A')}")

        if project.get("build_command"):
            print(f"   Build: {project['build_command']}")
        if project.get("lint_command"):
            print(f"   Lint: {project['lint_command']}")

        print()


def cmd_show(args):
    """Show detailed information about a specific project"""
    config = load_config(args.config)
    projects = get_projects(config)

    project = find_project(projects, args.project_id)
    if not project:
        print(f"Error: Project not found: {args.project_id}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Project: {project.get('name', 'Unnamed')}")
    print(f"{'='*80}\n")

    for key, value in project.items():
        if value is None or value == "":
            value = "(not set)"
        print(f"{key:20s}: {value}")

    print()


def cmd_add(args):
    """Add a new project"""
    config = load_config(args.config)

    # Ensure projects array exists
    if "projects" not in config:
        config["projects"] = []

    projects = config["projects"]

    # Check if project ID already exists
    if find_project(projects, args.id):
        print(f"Error: Project with ID '{args.id}' already exists", file=sys.stderr)
        sys.exit(1)

    # Build new project
    new_project = {
        "id": args.id,
        "name": args.name,
        "type": args.type,
        "path": args.path,
        "repository": args.repository,
        "git_platform": args.git_platform,
        "test_command": args.test_command,
        "build_command": args.build_command,
        "lint_command": args.lint_command,
        "format_command": args.format_command,
        "enabled": True,
    }

    # Validate
    errors = validate_project(new_project)
    if errors:
        print("Error: Invalid project configuration:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    # Add to config
    projects.append(new_project)
    config["projects"] = projects

    # Save
    save_config(args.config, config)
    print(f"✅ Project '{args.id}' added successfully")


def cmd_remove(args):
    """Remove a project"""
    config = load_config(args.config)
    projects = get_projects(config)

    project = find_project(projects, args.project_id)
    if not project:
        print(f"Error: Project not found: {args.project_id}", file=sys.stderr)
        sys.exit(1)

    # Confirm deletion
    if not args.yes:
        print(f"Are you sure you want to remove project '{args.project_id}'?")
        print(f"  Name: {project.get('name', 'N/A')}")
        print(f"  Path: {project.get('path', 'N/A')}")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != "yes":
            print("Cancelled.")
            return

    # Remove
    projects.remove(project)
    config["projects"] = projects

    # Save
    save_config(args.config, config)
    print(f"✅ Project '{args.project_id}' removed successfully")


def cmd_edit(args):
    """Edit a project field"""
    config = load_config(args.config)
    projects = get_projects(config)

    project = find_project(projects, args.project_id)
    if not project:
        print(f"Error: Project not found: {args.project_id}", file=sys.stderr)
        sys.exit(1)

    # Update field
    old_value = project.get(args.field, "(not set)")
    project[args.field] = args.value

    print(f"Field '{args.field}':")
    print(f"  Old: {old_value}")
    print(f"  New: {args.value}")

    # Validate
    errors = validate_project(project, allow_partial=True)
    if errors:
        print("Warning: Project validation issues:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)

        if not args.force:
            print("\nUse --force to save anyway", file=sys.stderr)
            sys.exit(1)

    # Save
    save_config(args.config, config)
    print(f"✅ Project '{args.project_id}' updated successfully")


def cmd_enable(args):
    """Enable a project"""
    config = load_config(args.config)
    projects = get_projects(config)

    project = find_project(projects, args.project_id)
    if not project:
        print(f"Error: Project not found: {args.project_id}", file=sys.stderr)
        sys.exit(1)

    if project.get("enabled", True):
        print(f"Project '{args.project_id}' is already enabled")
        return

    project["enabled"] = True

    save_config(args.config, config)
    print(f"✅ Project '{args.project_id}' enabled")


def cmd_disable(args):
    """Disable a project"""
    config = load_config(args.config)
    projects = get_projects(config)

    project = find_project(projects, args.project_id)
    if not project:
        print(f"Error: Project not found: {args.project_id}", file=sys.stderr)
        sys.exit(1)

    if not project.get("enabled", True):
        print(f"Project '{args.project_id}' is already disabled")
        return

    project["enabled"] = False

    save_config(args.config, config)
    print(f"✅ Project '{args.project_id}' disabled")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Lazy_Bird Project Manager - Manage multiple project configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all projects
  %(prog)s list

  # Show detailed info for a project
  %(prog)s show my-project

  # Add a new project
  %(prog)s add \\
    --id my-game \\
    --name "My Game Project" \\
    --type godot \\
    --path /home/user/projects/my-game \\
    --repository https://github.com/user/my-game \\
    --git-platform github \\
    --test-command "godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd --test-suite all"

  # Edit a project field
  %(prog)s edit my-game --field test_command --value "new test command"

  # Disable a project temporarily
  %(prog)s disable my-game

  # Re-enable a project
  %(prog)s enable my-game

  # Remove a project
  %(prog)s remove my-game
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".config" / "lazy_birtd" / "config.yml",
        help="Path to configuration file (default: ~/.config/lazy_birtd/config.yml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list command
    parser_list = subparsers.add_parser("list", help="List all projects")
    parser_list.set_defaults(func=cmd_list)

    # show command
    parser_show = subparsers.add_parser("show", help="Show detailed project information")
    parser_show.add_argument("project_id", help="Project ID")
    parser_show.set_defaults(func=cmd_show)

    # add command
    parser_add = subparsers.add_parser("add", help="Add a new project")
    parser_add.add_argument(
        "--id", required=True, help="Unique project ID (alphanumeric with dashes)"
    )
    parser_add.add_argument("--name", required=True, help="Project display name")
    parser_add.add_argument(
        "--type", required=True, help="Project type (godot, python, rust, nodejs, etc.)"
    )
    parser_add.add_argument("--path", required=True, help="Absolute path to project directory")
    parser_add.add_argument("--repository", required=True, help="Git repository URL")
    parser_add.add_argument(
        "--git-platform", required=True, choices=["github", "gitlab"], help="Git platform"
    )
    parser_add.add_argument("--test-command", required=True, help="Command to run tests")
    parser_add.add_argument("--build-command", help="Command to build (optional)")
    parser_add.add_argument("--lint-command", help="Command to lint code (optional)")
    parser_add.add_argument("--format-command", help="Command to format code (optional)")
    parser_add.set_defaults(func=cmd_add)

    # remove command
    parser_remove = subparsers.add_parser("remove", help="Remove a project")
    parser_remove.add_argument("project_id", help="Project ID to remove")
    parser_remove.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    parser_remove.set_defaults(func=cmd_remove)

    # edit command
    parser_edit = subparsers.add_parser("edit", help="Edit a project field")
    parser_edit.add_argument("project_id", help="Project ID")
    parser_edit.add_argument("--field", required=True, help="Field to edit")
    parser_edit.add_argument("--value", required=True, help="New value")
    parser_edit.add_argument(
        "--force", action="store_true", help="Force save even if validation fails"
    )
    parser_edit.set_defaults(func=cmd_edit)

    # enable command
    parser_enable = subparsers.add_parser("enable", help="Enable a project")
    parser_enable.add_argument("project_id", help="Project ID to enable")
    parser_enable.set_defaults(func=cmd_enable)

    # disable command
    parser_disable = subparsers.add_parser("disable", help="Disable a project")
    parser_disable.add_argument("project_id", help="Project ID to disable")
    parser_disable.set_defaults(func=cmd_disable)

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
