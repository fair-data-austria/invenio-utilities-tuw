"""Management commands for files."""

from collections import defaultdict

import click
from flask.cli import with_appcontext
from invenio_db import db
from invenio_files_rest.models import ObjectVersion, FileInstance
from invenio_rdm_records.services.services import (
    BibliographicRecordService as RecordService,
)

from .utils import convert_to_recid, get_identity_for_user


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
    help="persistent identifier of the record draft to operate on",
)


@click.group()
def files():
    """Utility commands for management of files."""
    pass


@files.command("rm")
@click.confirmation_option(
    prompt="are you sure you want to permanently remove soft-deleted files?"
)
@option_as_user
@option_pid_value
@option_pid_type
@with_appcontext
def hard_delete_files(user, pid, pid_type):
    """Hard-delete files that have already been soft-deleted.

    Optionally, this operation can be restricted to the bucket associated with a draft
    (via its PID).
    """
    recid = convert_to_recid(pid, pid_type) if pid else None
    service = RecordService()
    identity = get_identity_for_user(user)

    # if a PID was specified, limit the cleaning to this record's bucket
    marked_as_deleted = ObjectVersion.query.filter_by(file_id=None, is_head=True)
    if recid is not None:
        draft = service.read_draft(id_=recid, identity=identity)._record
        marked_as_deleted = marked_as_deleted.filter_by(bucket=draft.files.bucket)

    # check if the specified user has permissions
    service.require_permission(identity, "delete")

    # hard-delete all soft-deleted ObjectVersions
    file_instances = defaultdict(set)
    for dov in marked_as_deleted.all():
        for ov in ObjectVersion.get_versions(dov.bucket, dov.key).all():
            ov.remove()
            if ov.file is not None:
                file_instances[ov.key].add(ov.file)

    # delete the associated FileInstances, and remove files from disk
    for key in file_instances:
        for fi in file_instances[key]:
            try:
                storage = fi.storage()
                fi.delete()
                storage.delete()
                click.secho("{}\t{}".format(key, fi.uri), fg="red")
            except:
                click.secho("cannot delete file: %s" % fi.uri, fg="yellow")

    db.session.commit()


@files.group("orphans")
def orphans():
    """Management commands for orphaned files (without ObjectVersions)."""
    pass


@orphans.command("list")
@with_appcontext
def list_orphan_files(dry_run):
    """List files that aren't referenced in any records (anymore)."""
    for fi in (f for f in FileInstance.query.all() if not f.objects):
        click.secho(fi.uri, fg="yellow")


@orphans.command("clean")
@click.confirmation_option(
    prompt="are you sure you want to permanently remove orphaned files?"
)
@option_as_user
@with_appcontext
def clean_files(user):
    """Remove files that do not have associated ObjectVersions (anymore)."""
    service = RecordService()
    identity = get_identity_for_user(user)
    service = RecordService()
    service.require_permission(identity, "delete")

    for fi in (f for f in FileInstance.query.all() if not f.objects):
        try:
            storage = fi.storage()
            fi.delete()
            storage.delete()
            click.secho(fi.uri, fg="red")
        except:
            click.secho("cannot delete file: %s" % fi.uri, fg="yellow")
