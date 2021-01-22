"""Management commands for records."""

import json

import click
from flask.cli import with_appcontext
from invenio_files_rest.models import ObjectVersion

from ..utils import get_record_file_service, get_record_service
from .utils import (
    convert_to_recid,
    get_identity_for_user,
    get_object_uuid,
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
    help="persistent identifier of the record to operate on",
)
option_pid_values = click.option(
    "--pid",
    "-p",
    "pids",
    metavar="PID_VALUE",
    required=False,
    multiple=True,
    help="persistent identifier of the record to operate on (can be specified multiple times)",
)


@click.group()
def records():
    """Utility commands for creation and publication of drafts."""
    pass


@records.command("list")
@option_as_user
@with_appcontext
def list_records(user):
    """List all records accessible to the given user."""
    identity = get_identity_for_user(user)
    service = get_record_service()
    rec_model_cls = service.record_cls.model_cls

    recids = [
        rec.json["id"]
        for rec in rec_model_cls.query
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


@records.command("update")
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
    service = get_record_service()
    metadata = json.load(metadata_file)

    if patch:
        record_data = service.read(id_=pid, identity=identity).data.copy()
        metadata = patch_metadata(record_data, metadata)

    service.update(id_=pid, identity=identity, data=metadata)
    click.secho(pid, fg="green")


@records.command("delete")
@click.confirmation_option(prompt="are you sure you want to delete this record?")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def delete_record(pid, pid_type, user):
    """Delete the specified record."""
    identity = get_identity_for_user(user)
    recid = convert_to_recid(pid, pid_type)
    service = get_record_service()
    service.delete(id_=recid, identity=identity)

    click.secho(recid, fg="red")


@records.command("files")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def list_files(pid, pid_type, user):
    """Show a list of files deposited with the record."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_file_service()
    file_results = service.list_files(id_=recid, identity=identity)
    for f in file_results.entries:
        ov = ObjectVersion.get(f["bucket_id"], f["key"], f["version_id"])
        fi = ov.file
        click.secho("{}\t{}\t{}".format(ov.key, fi.uri, fi.checksum), fg="green")


@records.command("reindex")
@option_pid_values
@option_pid_type
@option_as_user
@with_appcontext
def reindex_records(pids, pid_type, user):
    """Reindex all available (or just the specified) records."""
    service = get_record_service()

    # basically, this is just a check whether the user exists,
    # since there's no permission for re-indexing
    get_identity_for_user(user)

    if pids:
        records = [
            service.record_cls.get_record(get_object_uuid(pid, pid_type))
            for pid in pids
        ]
    else:
        records = [
            service.record_cls.get_record(meta.id)
            for meta in service.record_cls.model_cls.query
            if meta is not None and meta.json is not None
        ]

    for record in records:
        service.indexer.index(record)