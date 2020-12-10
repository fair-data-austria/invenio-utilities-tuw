"""Management commands for drafts."""

import json
import os
import sys
from os.path import basename, isdir, isfile, join

import click
from flask.cli import with_appcontext
from invenio_rdm_records.records.models import DraftMetadata
from invenio_rdm_records.services.services import (
    BibliographicDraftFilesService as DraftFileService,
)
from invenio_rdm_records.services.services import (
    BibliographicRecordService as RecordService,
)

from .utils import (
    convert_to_recid,
    create_record_from_metadata,
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
def draft():
    """Utility commands for creation and publication of drafts."""
    pass


@draft.command("list")
@option_as_user
@with_appcontext
def list_draft(user):
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


@draft.command("create")
@click.argument("metadata_path", type=click.Path(exists=True))
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
    """Create a new record draft with the specified metadata.

    The specified metadata path can either point to a JSON file containing the metadata,
    or it can point to a directory.
    In the former case, no files will be added to the created draft.
    In the latter case, it is assumed that the directory contains a file called
    "metadata.json".
    Further, all files contained in the "files/" subdirectory will be added to the
    draft, if such a subdirectory exists.
    """
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
            exists = lambda fn: isfile(join(deposit_files_path, fn))
            content = os.listdir(deposit_files_path)
            file_names = [basename(fn) for fn in content if exists(fn)]

            if len(content) != len(file_names):
                ignored = [basename(fn) for fn in content if not exists(fn)]
                msg = "ignored in '{}': {}".format(deposit_files_path, ignored)
                click.secho(msg, fg="red", err=True)

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


@draft.command("update")
@click.argument("metadata_file", type=click.File("r"))
@option_pid_value
@option_pid_type
@option_as_user
@click.option(
    "--patch/--replace",
    "-p/-r",
    default=False,
    help="replace the draft's metadata entirely, or leave unmentioned fields as-is",
)
@with_appcontext
def update_draft(metadata_file, pid, pid_type, user, patch):
    """Update the specified draft's metadata."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = RecordService()
    metadata = json.load(metadata_file)

    if patch:
        draft_data = service.read_draft(id_=pid, identity=identity).data.copy()
        metadata = patch_metadata(draft_data, metadata)

    service.update_draft(id_=pid, identity=identity, data=metadata)
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


@draft.command("delete")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def delete_draft(pid, pid_type, user):
    """Delete the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = RecordService()
    service.delete_draft(id_=pid, identity=identity)
    click.secho(pid, fg="red")


@draft.group()
def files():
    """Manage files deposited with the draft."""
    pass


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
            exists = lambda fn: isfile(join(file_path, fn))
            content = os.listdir(file_path)
            file_names = [basename(fn) for fn in content if exists(fn)]

            if len(content) != len(file_names):
                ignored = [basename(fn) for fn in content if not exists(fn)]
                msg = "ignored in '{}': {}".format(file_path, ignored)
                click.secho(msg, fg="red", err=True)

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
        with open(fp, "rb") as deposit_file:
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
        click.echo("{}: {}".format(f["key"], f))
