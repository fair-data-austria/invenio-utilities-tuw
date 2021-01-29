# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Common options for CLI commands."""

import click

option_as_user = click.option(
    "--as-user",
    "-u",
    "user",
    metavar="USER",
    default=None,
    required=True,
    help="email address of the user to impersonate for the task",
)

option_pid_type = click.option(
    "--type",
    "-t",
    "pid_type",
    metavar="PID_TYPE",
    default="recid",
    help="pid type for the lookup (default: 'recid')",
)

option_pid_value = click.option(
    "--pid",
    "-p",
    "pid",
    metavar="PID_VALUE",
    required=True,
    help="persistent identifier of the object to operate on",
)

option_pid_values = click.option(
    "--pid",
    "-p",
    "pids",
    metavar="PID_VALUE",
    required=False,
    multiple=True,
    help="persistent identifier of the object to operate on (can be specified multiple times)",
)

option_owners = click.option(
    "--owner",
    "-o",
    "owners",
    metavar="OWNER",
    required=False,
    multiple=True,
    help="email address of the record owner to set (can be specified multiple times)",
)

# user management options

option_only_list_active_users = click.option(
    "--only-active/--include-inactive",
    "-a/-A",
    default=True,
    help="show only active users, or list all users",
)
option_hide_user_roles = click.option(
    "--show-roles/--hide-roles",
    "-r/-R",
    default=False,
    help="show (or hide) the roles associated with the users",
)
