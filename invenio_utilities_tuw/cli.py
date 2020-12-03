"""CLI commands for Invenio-Utilities-TUW."""

import json
import os
from os.path import basename

import click
from flask.cli import with_appcontext
from flask_principal import Identity
from invenio_access import any_user
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts
from invenio_pidstore.models import PersistentIdentifier
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


@click.group()
def utilities():
    """Utility commands for InvenioRDM."""
    pass


@utilities.group()
def draft():
    """Utility commands for creation and publication of drafts."""
    pass


@draft.command("create")
@click.argument("metadata_path")
@click.option(
    "--as-user",
    "-u",
    "user",
    default=None,
    metavar="USER",
    help="email address of the user to use for record creation (default: the first user)",
)
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

    if os.path.isfile(metadata_path):
        draft = create_record_from_metadata(metadata_path, identity)
        recid = draft["id"]

    elif os.path.isdir(metadata_path):
        metadata_file_path = os.path.join(metadata_path, "metadata.json")
        deposit_files_path = os.path.join(metadata_path, "files")
        if not os.path.isfile(metadata_file_path):
            raise Exception("metadata file does not exist: %s" % metadata_file_path)

        draft = create_record_from_metadata(metadata_file_path, identity)
        recid = draft["id"]
        file_names = []
        if os.path.isdir(deposit_files_path):
            file_names = [os.path.basename(fn) for fn in os.listdir(deposit_files_path)]

        service = DraftFileService()
        service.init_files(recid, identity, [{"key": fn} for fn in file_names])
        for fn in file_names:
            file_path = os.path.join(deposit_files_path, fn)
            with open(file_path, "rb") as deposit_file:
                service.set_file_content(recid, fn, identity, deposit_file)

            service.commit_file(recid, fn, identity)

    else:
        raise Exception("neither a file nor a directory: %s" % metadata_path)

    if publish:
        service = RecordService()
        service.publish(recid, identity)

    click.echo(recid)


@draft.command("publish")
@click.argument("pid", metavar="PID_VALUE")
@click.option(
    "--as-user",
    "-u",
    "user",
    default=None,
    metavar="USER",
    help="email address of the user to use for record creation (default: the first user)",
)
@click.option(
    "--type",
    "-t",
    "pid_type",
    default="recid",
    metavar="PID_TYPE",
    help="pid type (default: 'recid')",
)
@with_appcontext
def publish_draft(pid, pid_type, user):
    """Publish the specified draft."""
    if pid_type != "recid":
        pid = (
            PersistentIdentifier.query.filter_by(pid_value=pid, pid_type=pid_type)
            .first()
            .pid_value
        )
        pid_type = "recid"

    identity = get_identity_for_user(user)
    service = RecordService()
    service.publish(pid, identity)
    click.echo(pid)
