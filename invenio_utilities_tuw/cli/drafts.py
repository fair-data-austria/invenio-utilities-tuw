# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Management commands for drafts."""

import json
import os
import sys
from os.path import basename, isdir, isfile, join

import click
from flask.cli import with_appcontext
from invenio_files_rest.models import ObjectVersion

from ..utils import get_draft_file_service, get_record_service
from .options import (
    option_as_user,
    option_owners,
    option_pid_type,
    option_pid_value,
    option_pretty_print,
    option_vanity_pid,
)
from .utils import (
    convert_to_recid,
    create_record_from_metadata,
    get_identity_for_user,
    patch_metadata,
    read_metadata,
    set_record_owners,
)


@click.group()
def drafts():
    """Utility commands for creation and publication of drafts."""
    pass


@drafts.command("list")
@option_as_user
@with_appcontext
def list_drafts(user):
    """List all drafts accessible to the given user."""
    identity = get_identity_for_user(user)
    service = get_record_service()
    recids = [
        dm.json["id"]
        for dm in service.draft_cls.model_cls.query.all()
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


@drafts.command("create")
@click.argument("metadata_path", type=click.Path(exists=True))
@option_as_user
@click.option(
    "--publish",
    "-p",
    is_flag=True,
    default=False,
    help="publish the draft after creation (default: false)",
)
@option_owners
@option_vanity_pid
@with_appcontext
def create_draft(metadata_path, publish, user, owners, vanity_pid):
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
    if owners:
        owners = [get_identity_for_user(owner) for owner in owners]

    if isfile(metadata_path):
        metadata = read_metadata(metadata_path)
        if owners:
            metadata = set_record_owners(metadata, owners)

        draft = create_record_from_metadata(metadata, identity, vanity_pid=vanity_pid)
        recid = draft["id"]

    elif isdir(metadata_path):
        metadata_file_path = join(metadata_path, "metadata.json")
        deposit_files_path = join(metadata_path, "files")
        if not isfile(metadata_file_path):
            raise Exception("metadata file does not exist: %s" % metadata_file_path)

        metadata = read_metadata(metadata_file_path)
        if owners:
            metadata = set_record_owners(metadata, owners)

        draft = create_record_from_metadata(metadata, identity)
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

        service = get_draft_file_service()
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
        service = get_record_service()
        service.publish(id_=recid, identity=identity)

    click.secho(recid, fg="green")


@drafts.command("show")
@option_pid_value
@option_pid_type
@option_as_user
@option_pretty_print
@with_appcontext
def show_draft(pid, pid_type, user, pretty_print):
    """Show the stored data for the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_service()
    draft = service.read_draft(id_=pid, identity=identity)
    indent = 2 if pretty_print else None
    data = json.dumps(draft.data, indent=indent)
    click.echo(data)


@drafts.command("update")
@click.argument("metadata_file", type=click.File("r"))
@option_pid_value
@option_pid_type
@option_as_user
@click.option(
    "--patch/--replace",
    "-P/-R",
    default=False,
    help=(
        "replace the draft's metadata entirely, or leave unmentioned fields as-is "
        "(default: replace)"
    ),
)
@option_owners
@with_appcontext
def update_draft(metadata_file, pid, pid_type, user, patch, owners):
    """Update the specified draft's metadata."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_service()
    metadata = json.load(metadata_file)

    if patch:
        draft_data = service.read_draft(id_=pid, identity=identity).data.copy()
        metadata = patch_metadata(draft_data, metadata)

    if owners:
        owners = [get_identity_for_user(owner) for owner in owners]
        metadata = set_record_owners(metadata, owners)

    service.update_draft(id_=pid, identity=identity, data=metadata)
    click.secho(pid, fg="green")


@drafts.command("publish")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def publish_draft(pid, pid_type, user):
    """Publish the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_service()
    service.publish(id_=pid, identity=identity)
    click.secho(pid, fg="green")


@drafts.command("delete")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def delete_draft(pid, pid_type, user):
    """Delete the specified draft."""
    pid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_service()
    service.delete_draft(id_=pid, identity=identity)
    click.secho(pid, fg="red")


@drafts.group()
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
    service = get_draft_file_service()

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
    service = get_draft_file_service()

    for file_key in filekeys:
        service.delete_file(id_=recid, file_key=file_key, identity=identity)
        click.secho(file_key, fg="red")
        # TODO: add option for hard-deleting files


@files.command("list")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def list_files(pid, pid_type, user):
    """Show a list of files deposited with the draft."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_draft_file_service()
    file_results = service.list_files(id_=recid, identity=identity)
    for f in file_results.entries:
        ov = ObjectVersion.get(f["bucket_id"], f["key"], f["version_id"])
        fi = ov.file
        click.secho("{}\t{}\t{}".format(ov.key, fi.uri, fi.checksum), fg="green")


@files.command("verify")
@option_pid_value
@option_pid_type
@option_as_user
@with_appcontext
def verify_files(pid, pid_type, user):
    """Verify the checksums for each of the draft's files."""
    recid = convert_to_recid(pid, pid_type)
    identity = get_identity_for_user(user)
    service = get_record_service()
    service.require_permission(identity, "read_files")
    draft = service.read_draft(id_=recid, identity=identity)
    draft = draft._record if hasattr(draft, "_record") else draft
    num_errors = 0

    for name, rec_file in draft.files.entries.items():
        if rec_file.file.verify_checksum():
            click.secho(name, fg="green")
        else:
            click.secho("{}: failed checksum verification".format(name), fg="red")
            num_errors += 1

    if num_errors > 0:
        click.secho(
            "{} files failed the checksum verification".format(num_errors), fg="red"
        )
        sys.exit(1)
