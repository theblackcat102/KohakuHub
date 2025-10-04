"""Click-based CLI commands for KohakuHub."""

import json
import sys
import click
from rich.console import Console
from rich.table import Table

from .client import KohubClient
from .config import Config
from .errors import (
    KohubError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    AlreadyExistsError,
)

console = Console()


# Global options
@click.group()
@click.option("--endpoint", envvar="HF_ENDPOINT", help="KohakuHub endpoint URL")
@click.option("--token", envvar="HF_TOKEN", help="API token")
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.pass_context
def cli(ctx, endpoint, token, output):
    """KohakuHub CLI - Manage repositories, organizations, and users.

    Examples:

    \b
    # Login to KohakuHub
    kohub-cli auth login

    \b
    # Create a repository
    kohub-cli repo create my-org/my-model --type model

    \b
    # List repositories
    kohub-cli repo list --type model --author my-org

    \b
    # Launch interactive mode
    kohub-cli interactive

    For more help on a specific command, use:
    kohub-cli COMMAND --help
    """
    ctx.ensure_object(dict)
    config = Config()

    # Create client with provided options
    client = KohubClient(endpoint=endpoint, token=token, config=config)

    ctx.obj["client"] = client
    ctx.obj["output"] = output
    ctx.obj["console"] = console


def output_result(ctx, data, success_message=None):
    """Output result based on format preference."""
    output_format = ctx.obj.get("output", "text")

    if output_format == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        if success_message:
            console.print(success_message, style="bold green")
        elif isinstance(data, dict):
            for key, value in data.items():
                console.print(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                console.print(item)


def handle_error(e: Exception, ctx):
    """Handle CLI errors with appropriate output."""
    output_format = ctx.obj.get("output", "text")

    if output_format == "json":
        error_data = {
            "error": str(e),
            "type": type(e).__name__,
        }
        if isinstance(e, KohubError):
            error_data["status_code"] = e.status_code
        click.echo(json.dumps(error_data, indent=2))
    else:
        if isinstance(e, AuthenticationError):
            console.print(
                f"[bold red]Authentication Error:[/bold red] {e}",
            )
            console.print(
                "[yellow]Hint:[/yellow] Login with 'kohub-cli auth login' or set HF_TOKEN"
            )
        elif isinstance(e, AuthorizationError):
            console.print(f"[bold red]Permission Denied:[/bold red] {e}")
        elif isinstance(e, NotFoundError):
            console.print(f"[bold red]Not Found:[/bold red] {e}")
        elif isinstance(e, AlreadyExistsError):
            console.print(f"[bold red]Already Exists:[/bold red] {e}")
        else:
            console.print(f"[bold red]Error:[/bold red] {e}")

    sys.exit(1)


# ========== Auth Commands ==========


@cli.group()
def auth():
    """Authentication and user management."""
    pass


@auth.command()
@click.option("--username", prompt=True, help="Username")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.pass_context
def login(ctx, username, password):
    """Login to KohakuHub."""
    client = ctx.obj["client"]
    try:
        result = client.login(username, password)
        output_result(ctx, result, f"Logged in as {username}")
    except Exception as e:
        handle_error(e, ctx)


@auth.command()
@click.pass_context
def logout(ctx):
    """Logout from KohakuHub."""
    client = ctx.obj["client"]
    try:
        result = client.logout()
        output_result(ctx, result, "Logged out successfully")
    except Exception as e:
        handle_error(e, ctx)


@auth.command()
@click.pass_context
def whoami(ctx):
    """Show current user information."""
    client = ctx.obj["client"]
    try:
        user_info = client.whoami()
        if ctx.obj["output"] == "json":
            output_result(ctx, user_info)
        else:
            console.print(f"[bold]Username:[/bold] {user_info.get('username')}")
            console.print(f"[bold]Email:[/bold] {user_info.get('email')}")
            console.print(
                f"[bold]Email Verified:[/bold] {user_info.get('email_verified')}"
            )
            console.print(f"[bold]User ID:[/bold] {user_info.get('id')}")
    except Exception as e:
        handle_error(e, ctx)


@auth.group()
def token():
    """Manage API tokens."""
    pass


@token.command("create")
@click.option("--name", "-n", prompt=True, help="Token name")
@click.pass_context
def token_create(ctx, name):
    """Create a new API token."""
    client = ctx.obj["client"]
    try:
        result = client.create_token(name)
        token_value = result.get("token")

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            console.print(f"[bold green]Token created successfully![/bold green]")
            console.print(f"\n[bold]Token:[/bold] {token_value}")
            console.print(f"[bold]Name:[/bold] {name}")
            console.print(
                "\n[yellow]Save this token securely - you won't see it again![/yellow]"
            )
            console.print(
                "\n[bold]To use this token:[/bold]\nexport HF_TOKEN=" + token_value
            )
    except Exception as e:
        handle_error(e, ctx)


@token.command("list")
@click.pass_context
def token_list(ctx):
    """List all API tokens."""
    client = ctx.obj["client"]
    try:
        tokens = client.list_tokens()

        if ctx.obj["output"] == "json":
            output_result(ctx, tokens)
        else:
            if not tokens:
                console.print("[yellow]No tokens found[/yellow]")
                return

            table = Table(title="API Tokens")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Created", style="blue")
            table.add_column("Last Used", style="magenta")

            for t in tokens:
                table.add_row(
                    str(t.get("id")),
                    t.get("name", ""),
                    t.get("created_at", ""),
                    t.get("last_used", "Never"),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@token.command("delete")
@click.option("--id", "token_id", type=int, required=True, help="Token ID to delete")
@click.confirmation_option(prompt="Are you sure you want to delete this token?")
@click.pass_context
def token_delete(ctx, token_id):
    """Delete an API token."""
    client = ctx.obj["client"]
    try:
        result = client.revoke_token(token_id)
        output_result(ctx, result, f"Token {token_id} deleted successfully")
    except Exception as e:
        handle_error(e, ctx)


# ========== Repository Commands ==========


@cli.group()
def repo():
    """Repository management."""
    pass


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--private", is_flag=True, help="Make repository private")
@click.pass_context
def create(ctx, repo_id, repo_type, private):
    """Create a new repository.

    REPO_ID format: namespace/name or just name (uses your username)
    """
    client = ctx.obj["client"]
    try:
        result = client.create_repo(repo_id, repo_type=repo_type, private=private)
        output_result(ctx, result, f"Repository {repo_id} created successfully")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(
    prompt="Are you sure you want to delete this repository? This is irreversible!"
)
@click.pass_context
def delete(ctx, repo_id, repo_type):
    """Delete a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_repo(repo_id, repo_type=repo_type)
        output_result(ctx, result, f"Repository {repo_id} deleted successfully")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Specific revision/branch")
@click.pass_context
def info(ctx, repo_id, repo_type, revision):
    """Show repository information.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.repo_info(repo_id, repo_type=repo_type, revision=revision)
        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            from rich.panel import Panel
            from rich.text import Text

            # Build info display
            info_text = Text()

            # Repository header
            info_text.append(f"{result.get('id')}\n", style="bold cyan")
            info_text.append("─" * 60 + "\n", style="dim")

            # Basic info
            info_text.append("Author:        ", style="bold")
            info_text.append(f"{result.get('author')}\n")

            info_text.append("Type:          ", style="bold")
            info_text.append(f"{repo_type}\n")

            info_text.append("Visibility:    ", style="bold")
            visibility = "🔒 Private" if result.get("private") else "🌐 Public"
            info_text.append(f"{visibility}\n")

            info_text.append("Created:       ", style="bold")
            info_text.append(f"{result.get('createdAt', 'N/A')}\n")

            if result.get("lastModified"):
                info_text.append("Last Modified: ", style="bold")
                info_text.append(f"{result.get('lastModified')}\n")

            # Revision info
            if result.get("sha"):
                info_text.append("\n")
                info_text.append("Commit SHA:    ", style="bold")
                info_text.append(f"{result.get('sha')}\n", style="yellow")

            # Stats
            info_text.append("\n")
            info_text.append("Downloads:     ", style="bold")
            info_text.append(f"{result.get('downloads', 0)}\n")

            info_text.append("Likes:         ", style="bold")
            info_text.append(f"{result.get('likes', 0)}\n")

            # Tags
            if result.get("tags"):
                info_text.append("\nTags:          ", style="bold")
                info_text.append(f"{', '.join(result.get('tags'))}\n")

            panel = Panel(
                info_text,
                title=f"[bold]{repo_type.capitalize()} Repository[/bold]",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("list")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--author", help="Filter by author/namespace")
@click.option("--limit", default=50, help="Maximum number of results")
@click.pass_context
def list_repos(ctx, repo_type, author, limit):
    """List repositories."""
    client = ctx.obj["client"]
    try:
        repos = client.list_repos(repo_type=repo_type, author=author, limit=limit)

        if ctx.obj["output"] == "json":
            output_result(ctx, repos)
        else:
            if not repos:
                console.print("[yellow]No repositories found[/yellow]")
                return

            table = Table(title=f"{repo_type.capitalize()}s")
            table.add_column("Repository", style="cyan")
            table.add_column("Author", style="green")
            table.add_column("Private", style="yellow")
            table.add_column("Created", style="blue")

            for r in repos:
                table.add_row(
                    r.get("id", ""),
                    r.get("author", ""),
                    "Yes" if r.get("private") else "No",
                    r.get("createdAt", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@repo.command("ls")
@click.argument("namespace")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    help="Filter by repository type",
)
@click.pass_context
def list_namespace_repos(ctx, namespace, repo_type):
    """List all repositories under a namespace.

    NAMESPACE can be a username or organization name.

    Examples:
    \b
        kohub-cli repo ls my-org
        kohub-cli repo ls my-org --type model
    """
    client = ctx.obj["client"]
    try:
        repos = client.list_namespace_repos(namespace, repo_type=repo_type)

        if ctx.obj["output"] == "json":
            output_result(ctx, repos)
        else:
            if not repos:
                console.print(f"[yellow]No repositories found for {namespace}[/yellow]")
                return

            from rich.tree import Tree

            # Create tree root
            tree_root = Tree(
                f"[bold cyan]{namespace}[/bold cyan]'s repositories", guide_style="blue"
            )

            # Group by type if showing all types
            if repo_type is None:
                # Group repos by type
                by_type = {"model": [], "dataset": [], "space": []}
                for repo in repos:
                    rtype = repo.get("repo_type", "model")
                    by_type[rtype].append(repo)

                # Add to tree
                for rtype in ["model", "dataset", "space"]:
                    if by_type[rtype]:
                        type_node = tree_root.add(
                            f"[bold]{rtype.capitalize()}s[/bold] ({len(by_type[rtype])})"
                        )
                        for r in sorted(by_type[rtype], key=lambda x: x.get("id", "")):
                            visibility = "🔒" if r.get("private") else "🌐"
                            type_node.add(
                                f"{visibility} [cyan]{r.get('id')}[/cyan] [dim]({r.get('createdAt', 'N/A')})[/dim]"
                            )
            else:
                # Single type, flat list
                for r in sorted(repos, key=lambda x: x.get("id", "")):
                    visibility = "🔒" if r.get("private") else "🌐"
                    tree_root.add(
                        f"{visibility} [cyan]{r.get('id')}[/cyan] [dim]({r.get('createdAt', 'N/A')})[/dim]"
                    )

            console.print(tree_root)
            console.print(f"\n[dim]Total: {len(repos)} repositories[/dim]")
    except Exception as e:
        handle_error(e, ctx)


@repo.command()
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default="main", help="Branch or commit hash")
@click.option("--path", default="", help="Path within repository")
@click.option("--recursive", is_flag=True, help="List files recursively")
@click.pass_context
def files(ctx, repo_id, repo_type, revision, path, recursive):
    """List files in a repository.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.list_repo_tree(
            repo_id,
            repo_type=repo_type,
            revision=revision,
            path=path,
            recursive=recursive,
        )

        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            if not result:
                console.print("[yellow]No files found[/yellow]")
                return

            # Build tree structure
            from rich.tree import Tree

            def format_size(size_bytes):
                """Format file size in human-readable format."""
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

            # Create tree structure
            tree_root = Tree(
                f"[bold cyan]{repo_id}[/bold cyan] [dim]({revision})[/dim]",
                guide_style="blue",
            )

            # Build hierarchical structure
            if recursive:
                # Build tree from flat list
                tree_nodes = {".": tree_root}

                # Sort by path for better tree building
                sorted_items = sorted(result, key=lambda x: x.get("path", ""))

                for item in sorted_items:
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    item_size = item.get("size", 0)

                    # Split path into parts
                    parts = item_path.split("/")
                    parent_path = "/".join(parts[:-1]) if len(parts) > 1 else "."
                    name = parts[-1]

                    # Ensure parent exists
                    if parent_path not in tree_nodes:
                        # Create missing parent directories
                        parent_parts = parent_path.split("/")
                        for i in range(len(parent_parts)):
                            sub_path = "/".join(parent_parts[: i + 1])
                            if sub_path not in tree_nodes:
                                sub_parent = (
                                    "/".join(parent_parts[:i]) if i > 0 else "."
                                )
                                tree_nodes[sub_path] = tree_nodes[sub_parent].add(
                                    f"[bold blue]📁 {parent_parts[i]}[/bold blue]"
                                )

                    # Add item to tree
                    parent_node = tree_nodes.get(parent_path, tree_root)

                    if item_type == "directory":
                        tree_nodes[item_path] = parent_node.add(
                            f"[bold blue]📁 {name}[/bold blue]"
                        )
                    else:
                        # File with size and LFS indicator
                        size_str = format_size(item_size)
                        lfs_indicator = (
                            " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
                        )
                        parent_node.add(
                            f"[green]📄 {name}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
                        )
            else:
                # Simple flat list
                for item in sorted(
                    result,
                    key=lambda x: (x.get("type") != "directory", x.get("path", "")),
                ):
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    item_size = item.get("size", 0)

                    if item_type == "directory":
                        tree_root.add(f"[bold blue]📁 {item_path}[/bold blue]")
                    else:
                        size_str = format_size(item_size)
                        lfs_indicator = (
                            " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
                        )
                        tree_root.add(
                            f"[green]📄 {item_path}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
                        )

            console.print(tree_root)
    except Exception as e:
        handle_error(e, ctx)


# ========== Organization Commands ==========


@cli.group()
def org():
    """Organization management."""
    pass


@org.command()
@click.argument("org_name")
@click.option("--description", help="Organization description")
@click.pass_context
def create(ctx, org_name, description):
    """Create a new organization."""
    client = ctx.obj["client"]
    try:
        result = client.create_organization(org_name, description=description)
        output_result(ctx, result, f"Organization {org_name} created successfully")
    except Exception as e:
        handle_error(e, ctx)


@org.command()
@click.argument("org_name")
@click.pass_context
def info(ctx, org_name):
    """Show organization information."""
    client = ctx.obj["client"]
    try:
        result = client.get_organization(org_name)
        if ctx.obj["output"] == "json":
            output_result(ctx, result)
        else:
            console.print(f"[bold]Name:[/bold] {result.get('name')}")
            console.print(
                f"[bold]Description:[/bold] {result.get('description', 'N/A')}"
            )
            console.print(f"[bold]Created:[/bold] {result.get('created_at')}")
    except Exception as e:
        handle_error(e, ctx)


@org.command("list")
@click.option("--username", help="Username (defaults to current user)")
@click.pass_context
def list_orgs(ctx, username):
    """List user's organizations."""
    client = ctx.obj["client"]
    try:
        orgs = client.list_user_organizations(username=username)

        if ctx.obj["output"] == "json":
            output_result(ctx, orgs)
        else:
            if not orgs:
                console.print("[yellow]No organizations found[/yellow]")
                return

            table = Table(title="Organizations")
            table.add_column("Name", style="cyan")
            table.add_column("Role", style="green")
            table.add_column("Description", style="blue")

            for o in orgs:
                table.add_row(
                    o.get("name", ""),
                    o.get("role", ""),
                    o.get("description", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@org.group()
def member():
    """Manage organization members."""
    pass


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.option(
    "--role",
    type=click.Choice(["member", "admin", "super-admin"]),
    default="member",
    help="Member role",
)
@click.pass_context
def add(ctx, org_name, username, role):
    """Add a member to an organization."""
    client = ctx.obj["client"]
    try:
        result = client.add_organization_member(org_name, username, role=role)
        output_result(ctx, result, f"Added {username} to {org_name} as {role}")
    except Exception as e:
        handle_error(e, ctx)


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.confirmation_option(prompt="Are you sure you want to remove this member?")
@click.pass_context
def remove(ctx, org_name, username):
    """Remove a member from an organization."""
    client = ctx.obj["client"]
    try:
        result = client.remove_organization_member(org_name, username)
        output_result(ctx, result, f"Removed {username} from {org_name}")
    except Exception as e:
        handle_error(e, ctx)


@member.command()
@click.argument("org_name")
@click.argument("username")
@click.option(
    "--role",
    type=click.Choice(["member", "admin", "super-admin"]),
    required=True,
    help="New role",
)
@click.pass_context
def update(ctx, org_name, username, role):
    """Update a member's role."""
    client = ctx.obj["client"]
    try:
        result = client.update_organization_member(org_name, username, role=role)
        output_result(ctx, result, f"Updated {username}'s role in {org_name} to {role}")
    except Exception as e:
        handle_error(e, ctx)


# ========== Settings Commands ==========


@cli.group()
def settings():
    """Settings management for users, repos, and organizations."""
    pass


@settings.group()
def user():
    """User settings management."""
    pass


@user.command("update")
@click.option("--email", help="New email address")
@click.pass_context
def update_user(ctx, email):
    """Update user settings."""
    client = ctx.obj["client"]
    try:
        user_info = client.whoami()
        username = user_info["username"]

        result = client.update_user_settings(username=username, email=email)
        output_result(ctx, result, "User settings updated successfully")
    except Exception as e:
        handle_error(e, ctx)


@settings.group()
def repo():
    """Repository settings management."""
    pass


@repo.command("update")
@click.argument("repo_id")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--private/--public", default=None, help="Set repository visibility")
@click.option(
    "--gated",
    type=click.Choice(["auto", "manual", "none"]),
    help="Set gating mode",
)
@click.pass_context
def update_repo(ctx, repo_id, repo_type, private, gated):
    """Update repository settings.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        gated_value = None if gated == "none" else gated

        result = client.update_repo_settings(
            repo_id,
            repo_type=repo_type,
            private=private,
            gated=gated_value,
        )
        output_result(ctx, result, f"Repository {repo_id} settings updated")
    except Exception as e:
        handle_error(e, ctx)


@repo.command("move")
@click.argument("from_repo")
@click.argument("to_repo")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.pass_context
def move_repo(ctx, from_repo, to_repo, repo_type):
    """Move/rename a repository.

    FROM_REPO format: namespace/name
    TO_REPO format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.move_repo(
            from_repo=from_repo,
            to_repo=to_repo,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Repository moved from {from_repo} to {to_repo}")
    except Exception as e:
        handle_error(e, ctx)


@repo.group()
def branch():
    """Branch management."""
    pass


@branch.command("create")
@click.argument("repo_id")
@click.argument("branch")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Source revision (defaults to main)")
@click.pass_context
def create_branch(ctx, repo_id, branch, repo_type, revision):
    """Create a new branch.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.create_branch(
            repo_id,
            branch=branch,
            repo_type=repo_type,
            revision=revision,
        )
        output_result(ctx, result, f"Branch '{branch}' created in {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@branch.command("delete")
@click.argument("repo_id")
@click.argument("branch")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(prompt="Are you sure you want to delete this branch?")
@click.pass_context
def delete_branch(ctx, repo_id, branch, repo_type):
    """Delete a branch.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_branch(
            repo_id,
            branch=branch,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Branch '{branch}' deleted from {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@repo.group()
def tag():
    """Tag management."""
    pass


@tag.command("create")
@click.argument("repo_id")
@click.argument("tag")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.option("--revision", default=None, help="Source revision (defaults to main)")
@click.option("--message", "-m", help="Tag message")
@click.pass_context
def create_tag(ctx, repo_id, tag, repo_type, revision, message):
    """Create a new tag.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.create_tag(
            repo_id,
            tag=tag,
            repo_type=repo_type,
            revision=revision,
            message=message,
        )
        output_result(ctx, result, f"Tag '{tag}' created in {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@tag.command("delete")
@click.argument("repo_id")
@click.argument("tag")
@click.option(
    "--type",
    "repo_type",
    type=click.Choice(["model", "dataset", "space"]),
    default="model",
    help="Repository type",
)
@click.confirmation_option(prompt="Are you sure you want to delete this tag?")
@click.pass_context
def delete_tag(ctx, repo_id, tag, repo_type):
    """Delete a tag.

    REPO_ID format: namespace/name
    """
    client = ctx.obj["client"]
    try:
        result = client.delete_tag(
            repo_id,
            tag=tag,
            repo_type=repo_type,
        )
        output_result(ctx, result, f"Tag '{tag}' deleted from {repo_id}")
    except Exception as e:
        handle_error(e, ctx)


@settings.group()
def organization():
    """Organization settings management."""
    pass


@organization.command("update")
@click.argument("org_name")
@click.option("--description", help="New description")
@click.pass_context
def update_org(ctx, org_name, description):
    """Update organization settings."""
    client = ctx.obj["client"]
    try:
        result = client.update_organization_settings(
            org_name,
            description=description,
        )
        output_result(ctx, result, f"Organization {org_name} settings updated")
    except Exception as e:
        handle_error(e, ctx)


@organization.command("members")
@click.argument("org_name")
@click.pass_context
def list_org_members(ctx, org_name):
    """List organization members."""
    client = ctx.obj["client"]
    try:
        members = client.list_organization_members(org_name)

        if ctx.obj["output"] == "json":
            output_result(ctx, members)
        else:
            if not members:
                console.print("[yellow]No members found[/yellow]")
                return

            table = Table(title=f"{org_name} Members")
            table.add_column("Username", style="cyan")
            table.add_column("Role", style="green")

            for m in members:
                table.add_row(
                    m.get("user", ""),
                    m.get("role", ""),
                )

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


# ========== Configuration Commands ==========


@cli.group()
def config():
    """Configuration management."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Set a configuration value."""
    client = ctx.obj["client"]
    try:
        if key == "endpoint":
            client.config.endpoint = value
        elif key == "token":
            client.config.token = value
        else:
            client.config.set(key, value)

        output_result(ctx, {key: value}, f"Set {key} = {value}")
    except Exception as e:
        handle_error(e, ctx)


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Get a configuration value."""
    client = ctx.obj["client"]
    try:
        value = client.config.get(key)
        if value is None:
            console.print(f"[yellow]{key} is not set[/yellow]")
        else:
            output_result(ctx, {key: value})
    except Exception as e:
        handle_error(e, ctx)


@config.command("list")
@click.pass_context
def list_config(ctx):
    """Show all configuration."""
    client = ctx.obj["client"]
    try:
        cfg = client.load_config()
        cfg["endpoint"] = client.config.endpoint  # Include computed endpoint

        if ctx.obj["output"] == "json":
            output_result(ctx, cfg)
        else:
            console.print(f"[bold]Configuration file:[/bold] {client.config_path}\n")

            table = Table(title="Configuration")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")

            for key, value in cfg.items():
                # Mask token for security
                if key == "token" and value:
                    value = value[:10] + "..." if len(value) > 10 else "***"
                table.add_row(key, str(value))

            console.print(table)
    except Exception as e:
        handle_error(e, ctx)


@config.command()
@click.confirmation_option(prompt="Are you sure you want to clear all configuration?")
@click.pass_context
def clear(ctx):
    """Clear all configuration."""
    client = ctx.obj["client"]
    try:
        client.config.clear()
        output_result(ctx, {}, "Configuration cleared")
    except Exception as e:
        handle_error(e, ctx)


# ========== Interactive Mode ==========


@cli.command()
@click.pass_context
def interactive(ctx):
    """Launch interactive TUI mode.

    This provides a menu-driven interface for managing
    KohakuHub resources interactively.
    """
    # Import the interactive mode from main
    from .main import State, main_menu

    # Create state using current context settings
    state = State()

    # Override with any provided options
    if ctx.obj.get("client"):
        client = ctx.obj["client"]
        if client.endpoint != "http://localhost:8000":
            state.base_url = client.endpoint
        if client.token:
            state.session.headers["Authorization"] = f"Bearer {client.token}"

    # Launch interactive menu
    main_menu(state)
