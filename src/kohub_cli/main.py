import os
import json
from pathlib import Path

import click
import requests
import questionary
from rich.console import Console


class State:
    def __init__(self):
        self.session = requests.Session()
        self.console = Console()
        self.base_url = os.environ.get("HF_ENDPOINT", "http://127.0.0.1:8000")
        token = os.environ.get("HF_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

        # runtime user info (set on login or whoami)
        self.username = None

        # simple config/cred store under ~/.kohub-cli
        self.cfg_dir = Path.home() / ".kohub-cli"
        self.cfg_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.cfg_dir / "config.json"
        self.creds_path = self.cfg_dir / "credentials.json"

        # try to load config & creds and optionally auto-login
        self.config = self._load_json(self.config_path, default={})
        creds = self._load_json(self.creds_path, default=None)

        # allow persisting a custom endpoint
        if "base_url" in self.config:
            self.base_url = self.config["base_url"]

        # optional auto login with stored username/password
        if creds and creds.get("auto_login"):
            try:
                self._login_request(creds["username"], creds["password"])
                if not self.username:
                    self._refresh_whoami()
            except Exception as e:
                self.console.print(f"[yellow]Auto-login failed:[/yellow] {e}")

    def _load_json(self, path: Path, default):
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return default

    def _save_json(self, path: Path, data: dict, chmod_600: bool = False):
        path.write_text(json.dumps(data, indent=2))
        if chmod_600:
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass  # best effort on non-POSIX

    def _refresh_whoami(self):
        # GET /api/auth/me returns user info
        resp = self.session.get(f"{self.base_url}/api/auth/me")
        if resp.status_code == 200:
            self.username = resp.json().get("username")
        else:
            self.username = None

    def _login_request(self, username: str, password: str):
        r = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
        )
        if r.status_code != 200:
            try:
                detail = r.json().get("detail", "Login error")
            except Exception:
                detail = f"HTTP {r.status_code}"
            raise RuntimeError(detail)
        self.username = r.json().get("username")  # server should return it


pass_state = click.make_pass_decorator(State, ensure=True)


@click.group()
@pass_state
def cli(state: State):
    """kohub-cli"""
    pass


def main_menu(state: State):
    """Main menu"""
    while True:
        title = "What do you want to do?"
        if state.username:
            title = f"[{state.username}] - {title}"
        choice = questionary.select(
            title,
            choices=[
                "User Management",
                "Organization Management",
                "Repositories",
                "Settings",
                "Exit",
            ],
        ).ask()

        if choice == "User Management":
            user_menu(state)
        elif choice == "Organization Management":
            org_menu(state)
        elif choice == "Repositories":
            repo_menu(state)
        elif choice == "Settings":
            settings_menu(state)
        elif choice == "Exit":
            break


def user_menu(state: State):
    while True:
        choice = questionary.select(
            "User Management",
            choices=[
                "Register",
                "Login",
                "Create Token",
                "Who Am I",
                "My Organizations",
                "Logout",
                "Back",
            ],
        ).ask()

        if choice == "Register":
            register(state)
        elif choice == "Login":
            login(state)
        elif choice == "Create Token":
            create_token(state)
        elif choice == "Who Am I":
            whoami(state)
        elif choice == "My Organizations":
            my_orgs(state)
        elif choice == "Logout":
            logout(state)
        elif choice == "Back":
            break


def org_menu(state: State):
    while True:
        choice = questionary.select(
            "Organization Management",
            choices=[
                "Create Organization",
                "Add Member",
                "Remove Member",
                "Update Member Role",
                "Back",
            ],
        ).ask()

        if choice == "Create Organization":
            create_organization(state)
        elif choice == "Add Member":
            add_member(state)
        elif choice == "Remove Member":
            remove_member(state)
        elif choice == "Update Member Role":
            update_member_role(state)
        elif choice == "Back":
            break


def repo_menu(state: State):
    while True:
        choice = questionary.select(
            "Repositories",
            choices=[
                "Create Repo",
                "Delete Repo",
                "Repo Info",
                "List Files (Tree)",
                "Back",
            ],
        ).ask()

        if choice == "Create Repo":
            create_repo(state)
        elif choice == "Delete Repo":
            delete_repo(state)
        elif choice == "Repo Info":
            repo_info(state)
        elif choice == "List Files (Tree)":
            repo_tree(state)
        elif choice == "Back":
            break


def settings_menu(state: State):
    while True:
        choice = questionary.select(
            "Settings",
            choices=[
                "Set Base URL",
                "Save Credentials for Auto-Login",
                "Clear Saved Credentials",
                "Back",
            ],
        ).ask()

        if choice == "Set Base URL":
            base = questionary.text("Base URL (e.g., http://127.0.0.1:8000)").ask()
            if base:
                state.base_url = base.rstrip("/")
                state.config["base_url"] = state.base_url
                state._save_json(state.config_path, state.config, chmod_600=False)
                state.console.print(
                    f"Base URL set to {state.base_url}", style="bold green"
                )
        elif choice == "Save Credentials for Auto-Login":
            username = questionary.text("Username:").ask()
            password = questionary.password(
                "Password (stored locally, plain text):"
            ).ask()
            auto = questionary.confirm(
                "Enable auto-login on CLI start?", default=True
            ).ask()
            data = {
                "username": username,
                "password": password,
                "auto_login": bool(auto),
            }
            state._save_json(state.creds_path, data, chmod_600=True)
            state.console.print(
                f"Saved credentials at {state.creds_path}. Permissions set to 600.",
                style="bold yellow",
            )
        elif choice == "Clear Saved Credentials":
            try:
                if state.creds_path.exists():
                    state.creds_path.unlink()
                    state.console.print(
                        "Saved credentials removed.", style="bold green"
                    )
                else:
                    state.console.print("No saved credentials.", style="bold yellow")
            except Exception as e:
                state.console.print(
                    f"Error deleting credentials: {e}", style="bold red"
                )
        elif choice == "Back":
            break


# ===== User =====
def register(state: State):
    username = questionary.text("Username:").ask()
    email = questionary.text("Email:").ask()
    password = questionary.password("Password:").ask()

    response = requests.post(
        f"{state.base_url}/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    if response.status_code == 200:
        data = response.json()
        state.console.print(data.get("message", "Registered."), style="bold green")
        # Optional auto-login if email is already verified
        if data.get("email_verified", False):
            if questionary.confirm("Login now?", default=True).ask():
                try:
                    state._login_request(username, password)
                    state.console.print("Logged in.", style="bold green")
                    if questionary.confirm(
                        "Save credentials for future auto-login? (stored locally, plain text)",
                        default=False,
                    ).ask():
                        state._save_json(
                            state.creds_path,
                            {
                                "username": username,
                                "password": password,
                                "auto_login": True,
                            },
                            chmod_600=True,
                        )
                        state.console.print("Credentials saved.", style="bold yellow")
                except Exception as e:
                    state.console.print(f"Login failed: {e}", style="bold red")
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def login(state: State):
    username = questionary.text("Username:").ask()
    password = questionary.password("Password:").ask()

    try:
        state._login_request(username, password)
    except Exception as e:
        state.console.print(f"Error: {e}", style="bold red")
        return

    state.console.print("Logged in successfully.", style="bold green")
    if questionary.confirm(
        "Save credentials for future auto-login? (stored locally, plain text)",
        default=False,
    ).ask():
        state._save_json(
            state.creds_path,
            {"username": username, "password": password, "auto_login": True},
            chmod_600=True,
        )
        state.console.print(
            f"Saved credentials at {state.creds_path}.", style="bold yellow"
        )


def create_token(state: State):
    name = questionary.text("Token Name:").ask()

    response = state.session.post(
        f"{state.base_url}/api/auth/tokens/create",
        json={"name": name},
    )

    if response.status_code == 200:
        token = response.json().get("token")
        if token:
            state.console.print(f"Token created: {token}", style="bold green")
            state.console.print(
                "Please set this token as the HF_TOKEN environment variable.",
                style="bold yellow",
            )
        else:
            state.console.print("Token created.", style="bold green")
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def whoami(state: State):
    resp = state.session.get(f"{state.base_url}/api/auth/me")
    if resp.status_code == 200:
        info = resp.json()
        state.username = info.get("username")
        state.console.print(
            f"[bold green]You are[/bold green] {info.get('username')}  <{info.get('email')}>  "
            f"(email_verified={info.get('email_verified')})"
        )
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def my_orgs(state: State):
    if not state.username:
        state._refresh_whoami()
        if not state.username:
            state.console.print("Please login first.", style="bold red")
            return
    resp = state.session.get(f"{state.base_url}/org/users/{state.username}/orgs")
    if resp.status_code == 200:
        payload = resp.json()
        orgs = payload.get("organizations") or payload.get("orgs") or []
        if not orgs:
            state.console.print("You are not in any organizations.", style="yellow")
            return
        for o in orgs:
            name = o.get("name") or o.get("org") or "unknown"
            role = o.get("role") or "-"
            desc = o.get("description") or ""
            state.console.print(f"- {name} ({role}) — {desc}")
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def logout(state: State):
    resp = state.session.post(f"{state.base_url}/api/auth/logout")
    if resp.status_code == 200:
        state.username = None
        state.console.print("Logged out.", style="bold green")
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


# ===== Organizations =====
def create_organization(state: State):
    name = questionary.text("Organization Name:").ask()
    description = questionary.text("Description:").ask()

    response = state.session.post(
        f"{state.base_url}/org/create",
        json={"name": name, "description": description},
    )

    if response.status_code == 200:
        state.console.print(
            f"Organization '{name}' created successfully.", style="bold green"
        )
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def add_member(state: State):
    org = questionary.text("Organization:").ask()
    username = questionary.text("Username to add:").ask()
    role = questionary.select("Role:", choices=["member", "admin"]).ask()

    response = state.session.post(
        f"{state.base_url}/org/{org}/members/add",
        json={"username": username, "role": role},
    )

    if response.status_code == 200:
        state.console.print(f"Added {username} to {org} as {role}.", style="bold green")
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def remove_member(state: State):
    org = questionary.text("Organization:").ask()
    username = questionary.text("Username to remove:").ask()

    response = state.session.post(
        f"{state.base_url}/org/{org}/members/remove",
        json={"username": username},
    )

    if response.status_code == 200:
        state.console.print(f"Removed {username} from {org}.", style="bold green")
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def update_member_role(state: State):
    org = questionary.text("Organization:").ask()
    username = questionary.text("Username:").ask()
    role = questionary.select("New Role:", choices=["member", "admin"]).ask()

    response = state.session.post(
        f"{state.base_url}/org/{org}/members/update",
        json={"username": username, "role": role},
    )

    if response.status_code == 200:
        state.console.print(
            f"Updated role for {username} in {org} to {role}.", style="bold green"
        )
    else:
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = f"HTTP {response.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


# ===== Repositories =====
def create_repo(state: State):
    repo_type = questionary.select(
        "Repo type:", choices=["model", "dataset", "space"]
    ).ask()
    name = questionary.text("Repository Name:").ask()
    org = questionary.text("Organization (blank = your user namespace):").ask()
    private = questionary.confirm("Private repo?", default=False).ask()
    payload = {
        "type": repo_type,
        "name": name,
        "organization": org or None,
        "private": bool(private),
    }
    resp = state.session.post(f"{state.base_url}/api/repos/create", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        rid = data.get("repo_id") or data.get("id") or f"{org or '<you>'}/{name}"
        url = data.get("url") or "-"
        state.console.print(f"Created: {rid} → {url}", style="bold green")
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def delete_repo(state: State):
    repo_type = questionary.select(
        "Repo type:", choices=["model", "dataset", "space"]
    ).ask()
    namespace = questionary.text("Namespace (user/org):").ask()
    name = questionary.text("Repository Name:").ask()
    payload = {"type": repo_type, "name": name, "organization": namespace or None}
    if not questionary.confirm(
        f"Delete {namespace or '<your-user>'}/{name}? This is irreversible.",
        default=False,
    ).ask():
        return
    resp = state.session.delete(f"{state.base_url}/api/repos/delete", json=payload)
    if resp.status_code == 200:
        state.console.print("Repository deleted.", style="bold green")
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def repo_info(state: State):
    repo_type = questionary.select(
        "Repo type:", choices=["model", "dataset", "space"]
    ).ask()
    namespace = questionary.text("Namespace (user/org):").ask()
    name = questionary.text("Repository Name:").ask()
    resp = state.session.get(f"{state.base_url}/api/{repo_type}s/{namespace}/{name}")
    if resp.status_code == 200:
        state.console.print_json(data=resp.json())
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def repo_tree(state: State):
    repo_type = questionary.select(
        "Repo type:", choices=["model", "dataset", "space"]
    ).ask()
    namespace = questionary.text("Namespace (user/org):").ask()
    name = questionary.text("Repository Name:").ask()
    revision = questionary.text(
        "Revision/branch (default: main):", default="main"
    ).ask()
    path = questionary.text("Path (blank for repo root):", default="").ask()
    params = {"recursive": questionary.confirm("Recursive?", default=False).ask()}
    url = f"{state.base_url}/api/{repo_type}s/{namespace}/{name}/tree/{revision}/{path or ''}".rstrip(
        "/"
    )
    resp = state.session.get(url, params=params)
    if resp.status_code == 200:
        files = resp.json()
        if not files:
            state.console.print("No entries.", style="yellow")
        else:
            state.console.print_json(data=files)
    else:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = f"HTTP {resp.status_code}"
        state.console.print(f"Error: {detail}", style="bold red")


def main():
    """Main entry point for kohub-cli.

    If called without arguments, launches interactive TUI mode.
    Otherwise, uses Click CLI commands.
    """
    import sys

    # Check if any arguments were provided (excluding script name)
    # If no arguments, launch interactive mode
    if len(sys.argv) == 1:
        state = State()
        main_menu(state)
    else:
        # Use Click CLI
        from .cli import cli as click_cli

        click_cli()


if __name__ == "__main__":
    main()
