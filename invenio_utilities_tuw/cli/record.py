"""Management commands for records."""

import json

import click
from flask.cli import with_appcontext
from invenio_rdm_records.records.models import RecordMetadata
from invenio_rdm_records.services.services import (
    BibliographicRecordService as RecordService,
)

from .utils import (
    convert_to_recid,
    get_identity_for_user,
    patch_metadata,
)

option_as_user = click.option(
    "--as-user",
    "-u",
    "user",
    metavar="USER",
    default=None,
    required=True,
    help="email address of the user to use for record creation",
)
option_pid_type = click.option(
    "--type",
    "-t",
    "pid_type",
    metavar="PID_TYPE",
    default="recid",
    help="pid type (default: 'recid')",
)
option_pid_value = click.option(
    "--pid",
    "-p",
    "pid",
    metavar="PID_VALUE",
    required=True,
    help="persistent identifier of the record draft to operate on",
)


@click.group()
def record():
    """Utility commands for creation and publication of drafts."""
    pass


@record.command("list")
@option_as_user
@with_appcontext
def list_records(user):
    """List all records accessible to the given user."""
    identity = get_identity_for_user(user)
    service = RecordService()
    recids = [
        rec.json["id"]
        for rec in RecordMetadata.query.all()
        if rec is not None and rec.json is not None
    ]

    for recid in recids:
        try:
            rec = service.read(id_=recid, identity=identity)
            click.secho(
                "{} - {}".format(rec.id, rec.data["metadata"]["title"]), fg="green"
            )
        except:
            raise


@record.command("update")
@click.argument("metadata_file", type=click.File("r"))
@option_pid_value
@option_pid_type
@option_as_user
@click.option(
    "--patch/--replace",
    "-P/-R",
    default=False,
    help="replace the record's metadata entirely, or leave unmentioned fields as-is (default: replace)",
)
@with_appcontext
def update_record(metadata_file, pid, pid_type, user, patch):
    """Update the specified draft's metadata."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = RecordService()
    metadata = json.load(metadata_file)

    if patch:
        record_data = service.read(id_=pid, identity=identity).data.copy()
        metadata = patch_metadata(record_data, metadata)

    service.update(id_=pid, identity=identity, data=metadata)
    click.secho(pid, fg="green")


@record.command("delete")
@click.confirmation_option(prompt="are you sure you want to delete this record?")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def delete_record(pid, pid_type, user):
    """Delete the specified record."""
    identity = get_identity_for_user(user)
    recid = convert_to_recid(pid, pid_type)
    service = RecordService()
    service.delete(id_=recid, identity=identity)

    click.secho(recid, fg="red")
