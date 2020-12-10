"""CLI commands for Invenio-Utilities-TUW."""

import json
import os
import sys
from os.path import basename, join, isfile, isdir

import click
from flask.cli import with_appcontext
from flask_principal import Identity
from invenio_access import any_user
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts
from invenio_pidstore.models import PersistentIdentifier
from invenio_rdm_records.records.models import DraftMetadata
from invenio_rdm_records.services.services import (
    BibliographicDraftFilesService as DraftFileService,
)
from invenio_rdm_records.services.services import (
    BibliographicRecordService as RecordService,
)


def create_record_from_metadata(metadata_file_path, identity):
    """Create a draft from the metadata in the specified JSON file."""
    metadata = None
    with open(metadata_file_path, "r") as metadata_file:
        metadata = json.load(metadata_file)

    if metadata is None:
        raise Exception("not a valid json file: %s" % metadata_file_path)

    service = RecordService()
    draft = service.create(identity=identity, data=metadata)
    return draft


def get_identity_for_user(user):
    """Get the Identity for the user specified via email or ID."""
    identity = None
    if user is not None:
        # note: this seems like the canonical way to go
        #       'as_user' can be either an integer (id) or email address
        u = current_accounts.datastore.get_user(user)
        if u is not None:
            identity = get_identity(u)
        else:
            raise LookupError("user not found: %s" % user)

    if identity is None:
        identity = Identity(1)
        identity.provides.add(any_user)

    return identity


def convert_to_recid(pid_value, pid_type):
    if pid_type != "recid":
        pid_value = (
            PersistentIdentifier.query.filter_by(pid_value=pid, pid_type=pid_type)
            .first()
            .pid_value
        )

    return pid_value


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
def utilities():
    """Utility commands for InvenioRDM."""
    pass


@utilities.group()
def draft():
    """Utility commands for creation and publication of drafts."""
    pass


@draft.group()
def files():
    """Manage files deposited with the draft."""
    pass


@draft.command("create")
@click.argument("metadata_path")
@option_as_user
@click.option(
    "--publish",
    "-p",
    is_flag=True,
    default=False,
    help="publish the draft after creation (default: false)",
)
@with_appcontext
def create_draft(metadata_path, publish, user):
    """Create a new record draft with the specified metadata."""
    recid = None
    identity = get_identity_for_user(user)

    if isfile(metadata_path):
        draft = create_record_from_metadata(metadata_path, identity)
        recid = draft["id"]

    elif isdir(metadata_path):
        metadata_file_path = join(metadata_path, "metadata.json")
        deposit_files_path = join(metadata_path, "files")
        if not isfile(metadata_file_path):
            raise Exception("metadata file does not exist: %s" % metadata_file_path)

        draft = create_record_from_metadata(metadata_file_path, identity)
        recid = draft["id"]
        file_names = []
        if isdir(deposit_files_path):
            dir_contents = os.listdir(deposit_files_path)
            file_names = [basename(fn) for fn in dir_contents if isfile(join(deposit_files_path, fn))]
            if len(dir_contents) != len(file_names):
                ignored = [basename(fn) for fn in dir_contents if not isfile(join(deposit_files_path, fn))]
                click.secho(
                    "ignored in '{}': {}".format(deposit_files_path, ignored),
                    fg="red",
                    err=True,
                )

        service = DraftFileService()
        service.init_files(
            id_=recid, identity=identity, data=[{"key": fn} for fn in file_names]
        )
        for fn in file_names:
            file_path = join(deposit_files_path, fn)
            with open(file_path, "rb") as deposit_file:
                service.set_file_content(
                    id_=recid, file_key=fn, identity=identity, stream=deposit_file
                )

            service.commit_file(id_=recid, file_key=fn, identity=identity)

    else:
        raise Exception("neither a file nor a directory: %s" % metadata_path)

    if publish:
        service = RecordService()
        service.publish(id_=recid, identity=identity)

    click.secho(recid, fg="green")


@draft.command("list")
@option_as_user
@with_appcontext
def create_draft(user):
    """List all drafts accessible to the given user."""
    identity = get_identity_for_user(user)
    service = RecordService()
    recids = [
        dm.json["id"]
        for dm in DraftMetadata.query.all()
        if dm is not None and dm.json is not None
    ]

    for recid in recids:
        try:
            draft = service.read_draft(id_=recid, identity=identity)
            click.secho(
                "{} - {}".format(draft.id, draft.data["metadata"]["title"]), fg="green"
            )
        except:
            pass


@draft.command("delete")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def publish_draft(pid, pid_type, user):
    """Delete the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = RecordService()
    service.delete_draft(id_=pid, identity=identity)
    click.secho(pid, fg="green")


@draft.command("publish")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def publish_draft(pid, pid_type, user):
    """Publish the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = RecordService()
    service.publish(id_=pid, identity=identity)
    click.secho(pid, fg="green")


@files.command("add")
@click.argument("filepaths", metavar="PATH", type=click.Path(exists=True), nargs=-1)
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def add_files(filepaths, pid, pid_type, user):
    """Add the specified files to the draft."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = DraftFileService()

    paths = []
    for file_path in filepaths:
        if isdir(file_path):
            # add all files (no recursion into sub-dirs) from the directory
            dir_contents = os.listdir(file_path)
            file_names = [
                basename(fn) for fn in dir_contents if isfile(join(file_path, fn))
            ]
            if len(dir_contents) != len(file_names):
                ignored = [
                    basename(fn)
                    for fn in dir_contents
                    if not isfile(join(file_path, fn))
                ]
                click.secho(
                    "ignored in '{}': {}".format(file_path, ignored), fg="red", err=True
                )

            paths_ = [join(file_path, fn) for fn in file_names]
            paths.extend(paths_)

        elif isfile(file_path):
            paths.append(file_path)

    keys = [basename(fp) for fp in paths]
    if len(set(keys)) != len(keys):
        click.secho("aborting: duplicates in file names detected", fg="red", err=True)
        sys.exit(1)

    service.init_files(
        id_=recid, identity=identity, data=[{"key": basename(fp)} for fp in paths]
    )
    for fp in paths:
        fn = basename(fp)
        with open(file_path, "rb") as deposit_file:
            service.set_file_content(
                id_=recid, file_key=fn, identity=identity, stream=deposit_file
            )
        service.commit_file(id_=recid, file_key=fn, identity=identity)

    click.secho(recid, fg="green")


@files.command("remove")
@click.argument("filekeys", metavar="FILE", nargs=-1)
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def remove_files(filekeys, pid, pid_type, user):
    """Remove the deposited files."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = DraftFileService()

    for file_key in filekeys:
        service.delete_file(id_=recid, file_key=file_key, identity=identity)


@files.command("list")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def list_files(pid, pid_type, user):
    """Show a list of files deposited with the draft."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = DraftFileService()
    file_results = service.list_files(id_=recid, identity=identity)
    for f in file_results.entries:
        click.echo(f)
