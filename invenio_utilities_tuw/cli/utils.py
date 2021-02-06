# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Utilities for the CLI commands."""

import json

from flask_principal import Identity
from invenio_access import any_user
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier

from ..utils import get_record_service


def read_metadata(metadata_file_path):
    """Read the record metadata from the specified JSON file."""
    metadata = None
    with open(metadata_file_path, "r") as metadata_file:
        metadata = json.load(metadata_file)

    if metadata is None:
        raise Exception("not a valid json file: %s" % metadata_file_path)

    return metadata


def create_record_from_metadata(
    metadata, identity, vanity_pid=None, vanity_pid_type="recid"
):
    """Create a draft from the specified metadata."""
    service = get_record_service()

    if vanity_pid is not None:
        # check if the vanity PID is already taken, before doing anything stupid
        count = PersistentIdentifier.query.filter_by(
            pid_value=vanity_pid, pid_type=vanity_pid_type
        ).count()

        if count > 0:
            raise Exception(
                "PID '{}:{}' is already taken".format(vanity_pid_type, vanity_pid)
            )

    draft = service.create(identity=identity, data=metadata)
    actual_draft = draft._record if hasattr(draft, "_record") else draft

    if vanity_pid:
        # service.update_draft() is called to update the IDs in the record's metadata
        # (via record.commit()), re-index the record, and commit the db session
        if service.indexer:
            service.indexer.delete(actual_draft)

        actual_draft.pid.pid_value = vanity_pid
        db.session.commit()
        draft = service.update_draft(vanity_pid, identity=identity, data=metadata)

    return draft


def patch_metadata(metadata: dict, patch: dict) -> dict:
    """Replace the fields mentioned in the patch, while leaving others as is.

    The first argument's content will be changed during the process.
    """
    for key in patch.keys():
        val = patch[key]
        if isinstance(val, dict):
            patch_metadata(metadata[key], val)
        else:
            metadata[key] = val

    return metadata


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


def get_object_uuid(pid_value, pid_type):
    """Fetch the UUID of the referenced object."""
    uuid = (
        PersistentIdentifier.query.filter_by(pid_value=pid_value, pid_type=pid_type)
        .first()
        .object_uuid
    )

    return uuid


def convert_to_recid(pid_value, pid_type):
    """Fetch the recid of the referenced object."""
    if pid_type != "recid":
        object_uuid = get_object_uuid(pid_value=pid_value, pid_type=pid_type)
        query = PersistentIdentifier.query.filter_by(
            object_uuid=object_uuid,
            pid_type="recid",
        )
        pid_value = query.first().pid_value

    return pid_value


def set_record_owners(record_metadata, owners):
    """Set the record's owners, assuming an RDM-Records metadata schema."""
    metadata = record_metadata.copy()

    owners = [{"user": owner.id} for owner in owners]
    if "access" not in metadata:
        metadata["access"] = {}

    metadata["access"]["owned_by"] = owners
    return metadata


def _set_creatibutor_name(creatibutor):
    """Set the name from the given_name and family_name from the creator/contributor."""
    creatibutor = creatibutor.get("person_or_org", {})
    name = creatibutor.get("name")

    if not name:
        given_name = creatibutor.get("given_name")
        family_name = creatibutor.get("family_name")
        if given_name and family_name:
            creatibutor["name"] = "{}, {}".format(family_name, given_name)


def set_creatibutor_names(record_metadata):
    """Set the name field for each creator and contributor if they're not set."""
    metadata = record_metadata.copy()

    for creator in metadata.get("metadata", {}).get("creators", []):
        _set_creatibutor_name(creator)

    for contributor in metadata.get("metadata", {}).get("contributors", []):
        _set_creatibutor_name(contributor)

    return metadata
