# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""CLI commands for Invenio-Utilities-TUW."""

import click

from .drafts import drafts
from .files import files
from .records import records
from .users import users


@click.group()
def utilities():
    """Utility commands for InvenioRDM."""
    pass


utilities.add_command(drafts)
utilities.add_command(files)
utilities.add_command(records)
utilities.add_command(users)
