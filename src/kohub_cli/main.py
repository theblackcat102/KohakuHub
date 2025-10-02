import os
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


pass_state = click.make_pass_decorator(State, ensure=True)


@click.group()
@pass_state
def cli(state: State):
    """Kohaku Hub CLI"""
    pass


def main_menu(state: State):
    """Main menu"""
    while True:
        choice = questionary.select(
            "What do you want to do?",
            choices=["User Management", "Organization Management", "Exit"],
        ).ask()

        if choice == "User Management":
            user_menu(state)
        elif choice == "Organization Management":
            org_menu(state)
        elif choice == "Exit":
            break


def user_menu(state: State):
    choice = questionary.select(
        "User Management",
        choices=["Register", "Login", "Create Token", "Back"],
    ).ask()

    if choice == "Register":
        register(state)
    elif choice == "Login":
        login(state)
    elif choice == "Create Token":
        create_token(state)


def org_menu(state: State):
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


def register(state: State):
    username = questionary.text("Username:").ask()
    email = questionary.text("Email:").ask()
    password = questionary.password("Password:").ask()

    response = requests.post(
        f"{state.base_url}/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )

    if response.status_code == 200:
        state.console.print(response.json()["message"], style="bold green")
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def login(state: State):
    username = questionary.text("Username:").ask()
    password = questionary.password("Password:").ask()

    response = state.session.post(
        f"{state.base_url}/api/auth/login",
        json={"username": username, "password": password},
    )

    if response.status_code == 200:
        state.console.print(response.json()["message"], style="bold green")
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def create_token(state: State):
    name = questionary.text("Token Name:").ask()

    response = state.session.post(
        f"{state.base_url}/api/auth/tokens/create", json={"name": name}
    )

    if response.status_code == 200:
        token = response.json()["token"]
        state.console.print(f"Token created: {token}", style="bold green")
        state.console.print(
            "Please set this token as the HF_TOKEN environment variable.",
            style="bold yellow",
        )
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


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
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def add_member(state: State):
    org_name = questionary.text("Organization Name:").ask()
    username = questionary.text("Username:").ask()
    role = questionary.select("Role:", choices=["admin", "member", "visitor"]).ask()

    response = state.session.post(
        f"{state.base_url}/org/{org_name}/members",
        json={"username": username, "role": role},
    )

    if response.status_code == 200:
        state.console.print(
            f"User '{username}' added to '{org_name}' as '{role}'.",
            style="bold green",
        )
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def remove_member(state: State):
    org_name = questionary.text("Organization Name:").ask()
    username = questionary.text("Username:").ask()

    response = state.session.delete(
        f"{state.base_url}/org/{org_name}/members/{username}"
    )

    if response.status_code == 200:
        state.console.print(
            f"User '{username}' removed from '{org_name}'.", style="bold green"
        )
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def update_member_role(state: State):
    org_name = questionary.text("Organization Name:").ask()
    username = questionary.text("Username:").ask()
    role = questionary.select("Role:", choices=["admin", "member", "visitor"]).ask()

    response = state.session.put(
        f"{state.base_url}/org/{org_name}/members/{username}",
        json={"role": role},
    )

    if response.status_code == 200:
        state.console.print(
            f"User '{username}' in '{org_name}' now has role '{role}'.",
            style="bold green",
        )
    else:
        state.console.print(f"Error: {response.json()['detail']}", style="bold red")


def main():
    state = State()
    main_menu(state)
