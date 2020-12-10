"""Management commands for users."""

import click
from flask.cli import with_appcontext
from invenio_accounts.models import User


@click.group()
def users():
    """Management commands for users."""
    pass


@users.command("list")
@click.option(
    "--only-active/--include-inactive",
    "-a/-A",
    default=True,
    help="show only active users, or list all users",
)
@click.option(
    "--show-roles/--hide-roles",
    "-r/-R",
    default=False,
    help="show or hide the roles associated with the users",
)
@with_appcontext
def list_users(only_active, show_roles):
    """List registered users."""
    users = User.query

    if only_active:
        users = users.filter_by(active=True)

    for user in users:
        line = "{} {}".format(user.id, user.email)
        if show_roles:
            line += " {}".format([r.name for r in user.roles])

        fg = "green" if user.active else "red"
        click.secho(line, fg=fg)
