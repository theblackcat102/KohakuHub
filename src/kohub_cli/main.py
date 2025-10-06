"""Interactive TUI mode for KohakuHub CLI - Refactored version."""

import os
import sys
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .client import KohubClient
from .config import Config
from .errors import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    KohubError,
    NetworkError,
    NotFoundError,
)


class InteractiveState:
    """State management for interactive CLI mode."""

    def __init__(self):
        """Initialize interactive state with KohubClient."""
        self.console = Console()
        self.config = Config()

        # Initialize client
        endpoint = os.environ.get("HF_ENDPOINT") or self.config.endpoint
        token = os.environ.get("HF_TOKEN") or self.config.token

        self.client = KohubClient(endpoint=endpoint, token=token, config=self.config)
        self.username = None

        # Try to get current user if token exists
        if token:
            try:
                user_info = self.client.whoami()
                self.username = user_info.get("username")
            except Exception:
                # Token might be invalid, clear it
                self.console.print(
                    "[yellow]Stored token is invalid, please login again[/yellow]"
                )

    def render_header(self):
        """Render status header showing connection and user info."""
        # Connection status
        conn_text = Text()
        conn_text.append("🌐 ", style="bold blue")
        conn_text.append(self.client.endpoint)

        # User status
        user_text = Text()
        if self.username:
            user_text.append("👤 ", style="bold green")
            user_text.append(self.username, style="bold green")
        else:
            user_text.append("👤 ", style="bold red")
            user_text.append("Not logged in", style="bold red")

        # Combine in panel
        from rich.columns import Columns

        status = Columns([conn_text, user_text], equal=True, expand=True)

        panel = Panel(
            status,
            title="[bold]KohakuHub CLI[/bold]",
            border_style="blue",
            padding=(0, 2),
        )

        self.console.print(panel)
        self.console.print()

    def handle_error(self, e: Exception, operation: str = "Operation"):
        """Display error with helpful context.

        Args:
            e: Exception that occurred
            operation: Name of the operation that failed
        """
        error_text = Text()
        error_text.append("❌ ", style="bold red")
        error_text.append(f"{operation} failed\n\n", style="bold red")
        error_text.append(f"{str(e)}\n", style="red")

        # Add suggestions based on error type
        match e:
            case AuthenticationError():
                error_text.append("\n💡 Suggestions:\n", style="bold yellow")
                error_text.append("  • Login: Select 'Login' from User Management\n")
                error_text.append("  • Or create an API token and add to config\n")

            case NotFoundError():
                error_text.append("\n💡 Suggestions:\n", style="bold yellow")
                error_text.append("  • Check the resource name spelling\n")
                error_text.append("  • Verify the resource exists\n")

            case NetworkError():
                error_text.append("\n💡 Suggestions:\n", style="bold yellow")
                error_text.append(f"  • Check endpoint: {self.client.endpoint}\n")
                error_text.append("  • Verify server is running\n")
                error_text.append("  • Check your network connection\n")

        panel = Panel(
            error_text, title="[bold red]Error[/bold red]", border_style="red"
        )
        self.console.print(panel)
        input("\nPress Enter to continue...")


def main_menu(state: InteractiveState):
    """Main menu with improved UX."""
    while True:
        state.console.clear()
        state.render_header()

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("🔐 Authentication & User", value="auth"),
                questionary.Choice("📦 Repositories", value="repo"),
                questionary.Choice("👥 Organizations", value="org"),
                questionary.Choice("⚙️  Settings", value="settings"),
                questionary.Separator(),
                questionary.Choice("🚪 Exit", value="exit"),
            ],
        ).ask()

        match choice:
            case "auth":
                auth_menu(state)
            case "repo":
                repo_menu(state)
            case "org":
                org_menu(state)
            case "settings":
                settings_menu(state)
            case "exit":
                break


# ========== Authentication Menu ==========


def auth_menu(state: InteractiveState):
    """Authentication and user management menu."""
    while True:
        state.console.clear()
        state.render_header()

        # Show quick stats
        if state.username:
            state.console.print(f"[dim]Logged in as {state.username}[/dim]\n")

        choice = questionary.select(
            "Authentication & User Management",
            choices=[
                questionary.Choice("🔑 Login", value="login"),
                questionary.Choice("📝 Register", value="register"),
                questionary.Choice("ℹ️  Who Am I", value="whoami"),
                questionary.Separator("─── API Tokens ───"),
                questionary.Choice("➕ Create Token", value="create_token"),
                questionary.Choice("📋 List Tokens", value="list_tokens"),
                questionary.Choice("🗑️  Delete Token", value="delete_token"),
                questionary.Separator("─── Organizations ───"),
                questionary.Choice("👥 My Organizations", value="my_orgs"),
                questionary.Separator(),
                questionary.Choice("🚪 Logout", value="logout"),
                questionary.Choice("⬅️  Back", value="back"),
            ],
        ).ask()

        match choice:
            case "login":
                login(state)
            case "register":
                register(state)
            case "whoami":
                whoami(state)
            case "create_token":
                create_token(state)
            case "list_tokens":
                list_tokens(state)
            case "delete_token":
                delete_token(state)
            case "my_orgs":
                my_orgs(state)
            case "logout":
                logout(state)
            case "back":
                break


def login(state: InteractiveState):
    """Login with improved UX."""
    state.console.print("[bold]Login to KohakuHub[/bold]\n")

    username = questionary.text(
        "Username:", validate=lambda x: len(x) > 0 or "Username required"
    ).ask()

    password = questionary.password(
        "Password:", validate=lambda x: len(x) > 0 or "Password required"
    ).ask()

    # Login with progress
    with state.console.status("[bold green]Logging in..."):
        try:
            result = state.client.login(username, password)
            state.username = username
        except Exception as e:
            state.handle_error(e, "Login")
            return

    state.console.print(f"\n✓ Logged in as {username}", style="bold green")

    # Offer to create and save token
    if questionary.confirm(
        "\nCreate API token for future use? (Recommended)", default=True
    ).ask():
        token_name = questionary.text(
            "Token name:",
            default=f"cli-{os.uname().nodename if hasattr(os, 'uname') else 'windows'}",
        ).ask()

        try:
            with state.console.status("[bold green]Creating token..."):
                token_result = state.client.create_token(token_name)

            token_value = token_result["token"]

            # Save token to config
            state.config.token = token_value
            state.client.token = token_value

            state.console.print(
                "\n✓ Token created and saved to config", style="bold green"
            )
            state.console.print("[dim]You won't need to enter password again[/dim]")
        except Exception as e:
            state.console.print(f"\n[yellow]Token creation failed: {e}[/yellow]")

    input("\nPress Enter to continue...")


def register(state: InteractiveState):
    """Register new user with improved UX."""
    state.console.print("[bold]Register New Account[/bold]\n")

    username = questionary.text(
        "Username:",
        validate=lambda x: (
            len(x) >= 3 and len(x) <= 50 or "Username must be 3-50 characters"
        ),
    ).ask()

    email = questionary.text(
        "Email:", validate=lambda x: "@" in x or "Invalid email format"
    ).ask()

    password = questionary.password(
        "Password:",
        validate=lambda x: len(x) >= 6 or "Password must be at least 6 characters",
    ).ask()

    password_confirm = questionary.password("Confirm password:").ask()

    if password != password_confirm:
        state.console.print("\n✗ Passwords don't match", style="bold red")
        input("\nPress Enter to continue...")
        return

    # Register with progress
    with state.console.status("[bold green]Creating account..."):
        try:
            result = state.client.register(username, email, password)
        except AlreadyExistsError as e:
            state.handle_error(e, "Registration")
            return
        except Exception as e:
            state.handle_error(e, "Registration")
            return

    state.console.print(f"\n✓ Account created: {username}", style="bold green")

    message = result.get("message", "")
    if message:
        state.console.print(f"[dim]{message}[/dim]")

    # Auto-login if email is verified
    if result.get("email_verified", False):
        if questionary.confirm("\nLogin now?", default=True).ask():
            try:
                with state.console.status("[bold green]Logging in..."):
                    state.client.login(username, password)
                    state.username = username

                state.console.print("✓ Logged in", style="bold green")

                # Create and save token
                if questionary.confirm(
                    "Create API token? (Recommended)", default=True
                ).ask():
                    try:
                        token_result = state.client.create_token(f"cli-auto")
                        state.config.token = token_result["token"]
                        state.client.token = token_result["token"]
                        state.console.print(
                            "✓ Token created and saved", style="bold green"
                        )
                    except Exception:
                        pass
            except Exception as e:
                state.console.print(f"\n[yellow]Auto-login failed: {e}[/yellow]")

    input("\nPress Enter to continue...")


def whoami(state: InteractiveState):
    """Show current user info."""
    with state.console.status("[bold green]Fetching user info..."):
        try:
            info = state.client.whoami()
        except Exception as e:
            state.handle_error(e, "Get user info")
            return

    state.username = info.get("username")

    # Display in panel
    user_text = Text()
    user_text.append("👤 ", style="bold")
    user_text.append(f"{info.get('username')}\n\n", style="bold cyan")
    user_text.append("Email: ", style="bold")
    user_text.append(f"{info.get('email')}\n")
    user_text.append("Email Verified: ", style="bold")
    verified = "✓ Yes" if info.get("email_verified") else "✗ No"
    style = "green" if info.get("email_verified") else "yellow"
    user_text.append(f"{verified}\n", style=style)
    user_text.append("User ID: ", style="bold")
    user_text.append(f"{info.get('id')}\n")

    panel = Panel(
        user_text,
        title="[bold]Current User[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def create_token(state: InteractiveState):
    """Create API token with improved UX."""
    state.console.print("[bold]Create API Token[/bold]\n")
    state.console.print("[dim]Tokens allow programmatic access to KohakuHub[/dim]\n")

    name = questionary.text(
        "Token name (e.g., 'my-laptop', 'ci-server'):",
        validate=lambda x: len(x) > 0 or "Token name required",
    ).ask()

    # Create with progress
    with state.console.status("[bold green]Creating token..."):
        try:
            result = state.client.create_token(name)
        except Exception as e:
            state.handle_error(e, "Token creation")
            return

    token_value = result["token"]

    # Display token prominently
    token_display = Text()
    token_display.append("🔑 Your API Token:\n\n", style="bold yellow")
    token_display.append(token_value, style="bold green")
    token_display.append(
        "\n\n⚠️  Save this token now - you won't see it again!", style="bold red"
    )

    panel = Panel(
        token_display,
        title="[bold]Token Created Successfully[/bold]",
        border_style="green",
        padding=(1, 2),
    )

    state.console.print(panel)

    # Offer to save
    if questionary.confirm("\nSave token to config?", default=True).ask():
        state.config.token = token_value
        state.client.token = token_value
        state.console.print("✓ Token saved to config", style="bold green")

    state.console.print(f"\n[bold]To use this token:[/bold]")
    state.console.print(f"  export HF_TOKEN={token_value}")

    input("\nPress Enter to continue...")


def list_tokens(state: InteractiveState):
    """List all API tokens."""
    with state.console.status("[bold green]Fetching tokens..."):
        try:
            tokens = state.client.list_tokens()
        except Exception as e:
            state.handle_error(e, "List tokens")
            return

    if not tokens:
        state.console.print("[yellow]No tokens found[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Display in table
    from rich.table import Table

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

    state.console.print(table)
    input("\nPress Enter to continue...")


def delete_token(state: InteractiveState):
    """Delete an API token."""
    # First list tokens
    try:
        tokens = state.client.list_tokens()
    except Exception as e:
        state.handle_error(e, "List tokens")
        return

    if not tokens:
        state.console.print("[yellow]No tokens to delete[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Show tokens and let user select
    choices = []
    for t in tokens:
        label = f"{t['name']} (ID: {t['id']}, Created: {t.get('created_at', 'N/A')})"
        choices.append(questionary.Choice(label, value=t["id"]))
    choices.append(questionary.Choice("⬅️  Cancel", value=None))

    token_id = questionary.select("Select token to delete:", choices=choices).ask()

    if token_id is None:
        return

    # Confirm deletion
    if not questionary.confirm(
        f"Delete token ID {token_id}? This cannot be undone.", default=False
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Delete with progress
    with state.console.status("[bold green]Deleting token..."):
        try:
            state.client.revoke_token(token_id)
        except Exception as e:
            state.handle_error(e, "Token deletion")
            return

    state.console.print("\n✓ Token deleted successfully", style="bold green")
    input("\nPress Enter to continue...")


def my_orgs(state: InteractiveState):
    """Show user's organizations."""
    if not state.username:
        # Try to refresh
        try:
            info = state.client.whoami()
            state.username = info.get("username")
        except Exception:
            state.console.print("[bold red]Please login first[/bold red]")
            input("\nPress Enter to continue...")
            return

    with state.console.status("[bold green]Fetching organizations..."):
        try:
            orgs = state.client.list_user_organizations()
        except Exception as e:
            state.handle_error(e, "List organizations")
            return

    if not orgs:
        state.console.print("[yellow]You are not in any organizations[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{state.username}'s Organizations")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Description", style="blue")

    for o in orgs:
        table.add_row(
            o.get("name", ""),
            o.get("role", ""),
            o.get("description", ""),
        )

    state.console.print(table)
    input("\nPress Enter to continue...")


def logout(state: InteractiveState):
    """Logout from KohakuHub."""
    if not state.username:
        state.console.print("[yellow]Not logged in[/yellow]")
        input("\nPress Enter to continue...")
        return

    if not questionary.confirm(f"Logout from {state.username}?", default=True).ask():
        return

    with state.console.status("[bold green]Logging out..."):
        try:
            state.client.logout()
        except Exception as e:
            # Logout might fail if token-based, that's ok
            pass

    state.username = None
    state.console.print("\n✓ Logged out", style="bold green")
    input("\nPress Enter to continue...")


# ========== Organization Menu ==========


def org_menu(state: InteractiveState):
    """Organization management menu."""
    while True:
        state.console.clear()
        state.render_header()

        # Show quick stats
        if state.username:
            try:
                orgs = state.client.list_user_organizations()
                state.console.print(
                    f"[dim]You're in {len(orgs)} organization(s)[/dim]\n"
                )
            except Exception:
                pass

        choice = questionary.select(
            "Organization Management",
            choices=[
                questionary.Choice("➕ Create Organization", value="create"),
                questionary.Choice("📋 List My Organizations", value="list"),
                questionary.Choice("ℹ️  Organization Info", value="info"),
                questionary.Separator("─── Members ───"),
                questionary.Choice("👥 List Members", value="list_members"),
                questionary.Choice("➕ Add Member", value="add"),
                questionary.Choice("➖ Remove Member", value="remove"),
                questionary.Choice("🔄 Update Member Role", value="update_role"),
                questionary.Separator(),
                questionary.Choice("⬅️  Back", value="back"),
            ],
        ).ask()

        match choice:
            case "create":
                create_organization(state)
            case "list":
                my_orgs(state)
            case "info":
                organization_info(state)
            case "list_members":
                list_org_members(state)
            case "add":
                add_member(state)
            case "remove":
                remove_member(state)
            case "update_role":
                update_member_role(state)
            case "back":
                break


def create_organization(state: InteractiveState):
    """Create organization with improved UX."""
    state.console.print("[bold]Create Organization[/bold]\n")

    name = questionary.text(
        "Organization name:",
        validate=lambda x: (
            len(x) >= 3 and len(x) <= 50 or "Name must be 3-50 characters"
        ),
    ).ask()

    description = questionary.text("Description (optional):").ask()

    # Confirm
    state.console.print("\n[bold]Creating organization:[/bold]")
    state.console.print(f"  Name: {name}")
    if description:
        state.console.print(f"  Description: {description}")

    if not questionary.confirm("Proceed?", default=True).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Create with progress
    with state.console.status("[bold green]Creating organization..."):
        try:
            result = state.client.create_organization(name, description=description)
        except AlreadyExistsError:
            state.console.print(
                f"\n✗ Organization '{name}' already exists", style="bold red"
            )
            input("\nPress Enter to continue...")
            return
        except Exception as e:
            state.handle_error(e, "Organization creation")
            return

    state.console.print(
        f"\n✓ Organization '{name}' created successfully", style="bold green"
    )
    input("\nPress Enter to continue...")


def organization_info(state: InteractiveState):
    """Show organization information."""
    org_name = questionary.text("Organization name:").ask()

    with state.console.status("[bold green]Fetching organization info..."):
        try:
            info = state.client.get_organization(org_name)
        except Exception as e:
            state.handle_error(e, "Get organization info")
            return

    # Display
    info_text = Text()
    info_text.append("👥 ", style="bold")
    info_text.append(f"{info.get('name')}\n\n", style="bold cyan")
    info_text.append("Description: ", style="bold")
    info_text.append(f"{info.get('description', 'N/A')}\n")
    info_text.append("Created: ", style="bold")
    info_text.append(f"{info.get('created_at', 'N/A')}\n")

    panel = Panel(
        info_text,
        title="[bold]Organization Info[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def list_org_members(state: InteractiveState):
    """List organization members."""
    org_name = questionary.text("Organization name:").ask()

    with state.console.status("[bold green]Fetching members..."):
        try:
            members = state.client.list_organization_members(org_name)
        except Exception as e:
            state.handle_error(e, "List members")
            return

    if not members:
        state.console.print("[yellow]No members found[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{org_name} Members")
    table.add_column("Username", style="cyan")
    table.add_column("Role", style="green")

    for m in members:
        table.add_row(m.get("user", ""), m.get("role", ""))

    state.console.print(table)
    input("\nPress Enter to continue...")


def add_member(state: InteractiveState):
    """Add member to organization."""
    org_name = questionary.text("Organization name:").ask()
    username = questionary.text("Username to add:").ask()
    role = questionary.select(
        "Role:", choices=["member", "admin", "super-admin"], default="member"
    ).ask()

    # Confirm
    if not questionary.confirm(
        f"Add {username} to {org_name} as {role}?", default=True
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    with state.console.status("[bold green]Adding member..."):
        try:
            state.client.add_organization_member(org_name, username, role=role)
        except Exception as e:
            state.handle_error(e, "Add member")
            return

    state.console.print(
        f"\n✓ Added {username} to {org_name} as {role}", style="bold green"
    )
    input("\nPress Enter to continue...")


def remove_member(state: InteractiveState):
    """Remove member from organization."""
    org_name = questionary.text("Organization name:").ask()

    # Try to list members first
    try:
        members = state.client.list_organization_members(org_name)
        if members:
            # Let user select from list
            choices = [m["user"] for m in members]
            choices.append("⬅️  Cancel")
            username = questionary.select(
                "Select member to remove:", choices=choices
            ).ask()

            if username == "⬅️  Cancel":
                return
        else:
            username = questionary.text("Username to remove:").ask()
    except Exception:
        username = questionary.text("Username to remove:").ask()

    # Confirm
    if not questionary.confirm(
        f"⚠️  Remove {username} from {org_name}?", default=False
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    with state.console.status("[bold green]Removing member..."):
        try:
            state.client.remove_organization_member(org_name, username)
        except Exception as e:
            state.handle_error(e, "Remove member")
            return

    state.console.print(f"\n✓ Removed {username} from {org_name}", style="bold green")
    input("\nPress Enter to continue...")


def update_member_role(state: InteractiveState):
    """Update member role."""
    org_name = questionary.text("Organization name:").ask()
    username = questionary.text("Username:").ask()
    role = questionary.select(
        "New role:", choices=["member", "admin", "super-admin"]
    ).ask()

    # Confirm
    if not questionary.confirm(
        f"Update {username}'s role in {org_name} to {role}?", default=True
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    with state.console.status("[bold green]Updating role..."):
        try:
            state.client.update_organization_member(org_name, username, role=role)
        except Exception as e:
            state.handle_error(e, "Update member role")
            return

    state.console.print(f"\n✓ Updated {username}'s role to {role}", style="bold green")
    input("\nPress Enter to continue...")


# ========== Repository Menu ==========


def repo_menu(state: InteractiveState):
    """Repository management menu."""
    while True:
        state.console.clear()
        state.render_header()

        choice = questionary.select(
            "Repository Management",
            choices=[
                questionary.Choice("➕ Create Repository", value="create"),
                questionary.Choice("📋 List Repositories", value="list"),
                questionary.Choice("ℹ️  Repository Info", value="info"),
                questionary.Choice("📂 Browse Files", value="files"),
                questionary.Separator("─── Management ───"),
                questionary.Choice("⚙️  Repository Settings", value="settings"),
                questionary.Choice("🔄 Move/Rename", value="move"),
                questionary.Choice("🗑️  Delete Repository", value="delete"),
                questionary.Separator(),
                questionary.Choice("⬅️  Back", value="back"),
            ],
        ).ask()

        match choice:
            case "create":
                create_repo(state)
            case "list":
                list_repos(state)
            case "info":
                repo_info(state)
            case "files":
                repo_tree(state)
            case "settings":
                repo_settings(state)
            case "move":
                move_repo(state)
            case "delete":
                delete_repo(state)
            case "back":
                break


def create_repo(state: InteractiveState):
    """Create repository with improved UX."""
    state.console.print("[bold]Create Repository[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    name = questionary.text(
        "Repository name:",
        validate=lambda x: (
            len(x) > 0 and len(x) < 100 or "Name must be 1-100 characters"
        ),
    ).ask()

    # Default to current user's namespace
    namespace = questionary.text(
        "Namespace (organization or username):", default=state.username or ""
    ).ask()

    private = questionary.confirm("Private repository?", default=False).ask()

    repo_id = f"{namespace}/{name}"

    # Show summary
    state.console.print("\n[bold]Creating repository:[/bold]")
    state.console.print(f"  Type: {repo_type}")
    state.console.print(f"  ID: {repo_id}")
    state.console.print(f"  Visibility: {'🔒 Private' if private else '🌐 Public'}")

    if not questionary.confirm("\nProceed?", default=True).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Create with progress
    with state.console.status("[bold green]Creating repository..."):
        try:
            result = state.client.create_repo(
                repo_id, repo_type=repo_type, private=private
            )
        except AlreadyExistsError:
            state.console.print(
                f"\n✗ Repository {repo_id} already exists", style="bold red"
            )
            input("\nPress Enter to continue...")
            return
        except Exception as e:
            state.handle_error(e, "Repository creation")
            return

    state.console.print(
        f"\n✓ Repository created: {result.get('url')}", style="bold green"
    )
    input("\nPress Enter to continue...")


def list_repos(state: InteractiveState):
    """List repositories."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    author = questionary.text("Filter by author (optional, leave blank for all):").ask()

    with state.console.status("[bold green]Fetching repositories..."):
        try:
            repos = state.client.list_repos(
                repo_type=repo_type, author=author or None, limit=50
            )
        except Exception as e:
            state.handle_error(e, "List repositories")
            return

    if not repos:
        state.console.print("[yellow]No repositories found[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Display in table
    from rich.table import Table

    table = Table(title=f"{repo_type.capitalize()}s")
    table.add_column("Repository", style="cyan")
    table.add_column("Author", style="green")
    table.add_column("Visibility", style="yellow")
    table.add_column("Created", style="blue")

    for r in repos:
        visibility = "🔒 Private" if r.get("private") else "🌐 Public"
        table.add_row(
            r.get("id", ""),
            r.get("author", ""),
            visibility,
            r.get("createdAt", ""),
        )

    state.console.print(table)
    state.console.print(f"\n[dim]Total: {len(repos)} repositories[/dim]")
    input("\nPress Enter to continue...")


def repo_info(state: InteractiveState):
    """Show repository information."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        "Repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    with state.console.status("[bold green]Fetching repository info..."):
        try:
            info = state.client.repo_info(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Get repository info")
            return

    # Display
    info_text = Text()
    info_text.append("📦 ", style="bold")
    info_text.append(f"{info.get('id')}\n\n", style="bold cyan")

    info_text.append("Author: ", style="bold")
    info_text.append(f"{info.get('author')}\n")

    info_text.append("Type: ", style="bold")
    info_text.append(f"{repo_type}\n")

    info_text.append("Visibility: ", style="bold")
    visibility = "🔒 Private" if info.get("private") else "🌐 Public"
    info_text.append(f"{visibility}\n")

    info_text.append("Created: ", style="bold")
    info_text.append(f"{info.get('createdAt', 'N/A')}\n")

    if info.get("lastModified"):
        info_text.append("Last Modified: ", style="bold")
        info_text.append(f"{info.get('lastModified')}\n")

    if info.get("sha"):
        info_text.append("\nCommit SHA: ", style="bold")
        info_text.append(f"{info.get('sha')}\n", style="yellow")

    panel = Panel(
        info_text,
        title=f"[bold]{repo_type.capitalize()} Repository[/bold]",
        border_style="cyan",
        padding=(1, 2),
    )

    state.console.print(panel)
    input("\nPress Enter to continue...")


def repo_tree(state: InteractiveState):
    """Browse repository files with tree view."""
    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        "Repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    revision = questionary.text("Revision/branch:", default="main").ask()

    path = questionary.text("Path (leave blank for root):", default="").ask()

    recursive = questionary.confirm("List recursively?", default=False).ask()

    with state.console.status("[bold green]Fetching file tree..."):
        try:
            files = state.client.list_repo_tree(
                repo_id,
                repo_type=repo_type,
                revision=revision,
                path=path,
                recursive=recursive,
            )
        except Exception as e:
            state.handle_error(e, "List files")
            return

    if not files:
        state.console.print("[yellow]No files found[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Display as tree
    from rich.tree import Tree

    def format_size(size_bytes):
        """Format file size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    tree_root = Tree(
        f"[bold cyan]{repo_id}[/bold cyan] [dim]({revision})[/dim]",
        guide_style="blue",
    )

    for item in sorted(
        files, key=lambda x: (x.get("type") != "directory", x.get("path", ""))
    ):
        item_path = item.get("path", "")
        item_type = item.get("type", "")
        item_size = item.get("size", 0)

        if item_type == "directory":
            tree_root.add(f"[bold blue]📁 {item_path}[/bold blue]")
        else:
            size_str = format_size(item_size)
            lfs_indicator = " [yellow](LFS)[/yellow]" if item.get("lfs") else ""
            tree_root.add(
                f"[green]📄 {item_path}[/green] [dim]({size_str})[/dim]{lfs_indicator}"
            )

    state.console.print(tree_root)
    state.console.print(f"\n[dim]Total: {len(files)} items[/dim]")
    input("\nPress Enter to continue...")


def repo_settings(state: InteractiveState):
    """Update repository settings."""
    state.console.print("[bold]Repository Settings[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        "Repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    # Get current settings
    try:
        info = state.client.repo_info(repo_id, repo_type=repo_type)
        current_private = info.get("private", False)
    except Exception:
        current_private = False

    state.console.print(
        f"\n[dim]Current visibility: {'Private' if current_private else 'Public'}[/dim]\n"
    )

    private = questionary.select(
        "Visibility:",
        choices=[
            questionary.Choice("🌐 Public", value=False),
            questionary.Choice("🔒 Private", value=True),
        ],
        default=current_private,
    ).ask()

    # Confirm
    if not questionary.confirm("Update settings?", default=True).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    with state.console.status("[bold green]Updating settings..."):
        try:
            state.client.update_repo_settings(
                repo_id, repo_type=repo_type, private=private
            )
        except Exception as e:
            state.handle_error(e, "Update settings")
            return

    state.console.print("\n✓ Settings updated", style="bold green")
    input("\nPress Enter to continue...")


def move_repo(state: InteractiveState):
    """Move/rename repository."""
    state.console.print("[bold]Move/Rename Repository[/bold]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    from_repo = questionary.text(
        "Current repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    to_repo = questionary.text(
        "New repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    # Confirm
    state.console.print(f"\n[bold]Move repository:[/bold]")
    state.console.print(f"  From: {from_repo}")
    state.console.print(f"  To: {to_repo}")

    if not questionary.confirm("\n⚠️  Proceed?", default=False).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    with state.console.status("[bold green]Moving repository..."):
        try:
            result = state.client.move_repo(
                from_repo=from_repo, to_repo=to_repo, repo_type=repo_type
            )
        except Exception as e:
            state.handle_error(e, "Move repository")
            return

    state.console.print(
        f"\n✓ Repository moved: {result.get('url')}", style="bold green"
    )
    input("\nPress Enter to continue...")


def delete_repo(state: InteractiveState):
    """Delete repository with improved confirmation."""
    state.console.print("[bold red]Delete Repository[/bold red]\n")
    state.console.print("[yellow]⚠️  This action is IRREVERSIBLE![/yellow]\n")

    repo_type = questionary.select(
        "Repository type:", choices=["model", "dataset", "space"], default="model"
    ).ask()

    repo_id = questionary.text(
        "Repository ID (namespace/name):",
        validate=lambda x: "/" in x or "Format: namespace/name",
    ).ask()

    # Try to show repo info first
    try:
        info = state.client.repo_info(repo_id, repo_type=repo_type)
        state.console.print("[bold]Repository to delete:[/bold]")
        state.console.print(f"  ID: {info.get('id')}")
        state.console.print(f"  Type: {repo_type}")
        state.console.print(
            f"  Visibility: {'Private' if info.get('private') else 'Public'}"
        )
        if info.get("lastModified"):
            state.console.print(f"  Last Modified: {info.get('lastModified')}")
        state.console.print()
    except Exception:
        pass

    # Double confirmation
    if not questionary.confirm(
        f"⚠️  Delete {repo_id}? This CANNOT be undone!", default=False
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    # Type repo name to confirm
    repo_name = repo_id.split("/")[1]
    confirmation = questionary.text(
        f"Type the repository name '{repo_name}' to confirm:",
    ).ask()

    if confirmation != repo_name:
        state.console.print(
            "\n✗ Repository name doesn't match. Deletion cancelled.",
            style="bold red",
        )
        input("\nPress Enter to continue...")
        return

    # Delete with progress
    with state.console.status("[bold red]Deleting repository..."):
        try:
            state.client.delete_repo(repo_id, repo_type=repo_type)
        except Exception as e:
            state.handle_error(e, "Repository deletion")
            return

    state.console.print(f"\n✓ Repository {repo_id} deleted", style="bold green")
    input("\nPress Enter to continue...")


# ========== Settings Menu ==========


def settings_menu(state: InteractiveState):
    """Settings and configuration menu."""
    while True:
        state.console.clear()
        state.render_header()

        state.console.print(f"[dim]Config: {state.client.config.config_file}[/dim]\n")

        choice = questionary.select(
            "Settings & Configuration",
            choices=[
                questionary.Choice("🌐 Set Endpoint URL", value="endpoint"),
                questionary.Choice("🔑 Set API Token", value="token"),
                questionary.Choice("📋 Show All Config", value="show"),
                questionary.Choice("🗑️  Clear Config", value="clear"),
                questionary.Separator(),
                questionary.Choice("⬅️  Back", value="back"),
            ],
        ).ask()

        match choice:
            case "endpoint":
                set_endpoint(state)
            case "token":
                set_token(state)
            case "show":
                show_config(state)
            case "clear":
                clear_config(state)
            case "back":
                break


def set_endpoint(state: InteractiveState):
    """Set endpoint URL."""
    current = state.client.endpoint
    state.console.print(f"[dim]Current endpoint: {current}[/dim]\n")

    endpoint = questionary.text(
        "Endpoint URL (e.g., http://localhost:48888):",
        default=current,
        validate=lambda x: x.startswith("http")
        or "Must start with http:// or https://",
    ).ask()

    endpoint = endpoint.rstrip("/")
    state.config.endpoint = endpoint
    state.client.endpoint = endpoint

    state.console.print(f"\n✓ Endpoint set to {endpoint}", style="bold green")
    input("\nPress Enter to continue...")


def set_token(state: InteractiveState):
    """Set API token."""
    state.console.print("[bold]Set API Token[/bold]\n")
    state.console.print("[dim]Token will be saved to config file[/dim]\n")

    token = questionary.password(
        "API Token:", validate=lambda x: len(x) > 0 or "Token required"
    ).ask()

    # Test token
    state.config.token = token
    state.client.token = token

    with state.console.status("[bold green]Verifying token..."):
        try:
            user_info = state.client.whoami()
            state.username = user_info.get("username")
        except Exception as e:
            state.console.print(f"\n✗ Invalid token: {e}", style="bold red")
            input("\nPress Enter to continue...")
            return

    state.console.print(
        f"\n✓ Token saved and verified (user: {state.username})", style="bold green"
    )
    input("\nPress Enter to continue...")


def show_config(state: InteractiveState):
    """Show all configuration."""
    cfg = state.client.load_config()
    cfg["endpoint"] = state.client.endpoint

    from rich.table import Table

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in cfg.items():
        # Mask token
        if key == "token" and value:
            value = value[:10] + "..." if len(value) > 10 else "***"
        table.add_row(key, str(value))

    state.console.print(table)
    state.console.print(f"\n[dim]Config file: {state.client.config.config_file}[/dim]")
    input("\nPress Enter to continue...")


def clear_config(state: InteractiveState):
    """Clear all configuration."""
    if not questionary.confirm(
        "⚠️  Clear all configuration? This will logout and remove saved token.",
        default=False,
    ).ask():
        state.console.print("[yellow]Cancelled[/yellow]")
        input("\nPress Enter to continue...")
        return

    state.client.config.clear()
    state.client.token = None
    state.username = None

    state.console.print("\n✓ Configuration cleared", style="bold green")
    input("\nPress Enter to continue...")


def main():
    """Main entry point for interactive mode."""
    if len(sys.argv) == 1:
        state = InteractiveState()
        main_menu(state)
    else:
        # Use Click CLI
        from .cli import cli as click_cli

        click_cli()


if __name__ == "__main__":
    main()
