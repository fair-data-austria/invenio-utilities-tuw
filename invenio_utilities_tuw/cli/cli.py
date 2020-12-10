"""CLI commands for Invenio-Utilities-TUW."""

import click

from .draft import draft
from .users import users


@click.group()
def utilities():
    """Utility commands for InvenioRDM."""
    pass


utilities.add_command(draft)
utilities.add_command(users)