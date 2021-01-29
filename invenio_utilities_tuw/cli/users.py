# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Management commands for users."""

import click
from flask.cli import with_appcontext
from invenio_accounts.models import User

from .options import option_hide_user_roles, option_only_list_active_users


@click.group()
def users():
    """Management commands for users."""
    pass


@users.command("list")
@option_only_list_active_users
@option_hide_user_roles
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
