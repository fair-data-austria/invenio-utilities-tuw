"""Utilities for the CLI commands."""

import json

from flask_principal import Identity
from invenio_access import any_user
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts
from invenio_pidstore.models import PersistentIdentifier

from ..utils import get_record_service


def create_record_from_metadata(metadata_file_path, identity):
    """Create a draft from the metadata in the specified JSON file."""
    metadata = None
    with open(metadata_file_path, "r") as metadata_file:
        metadata = json.load(metadata_file)

    if metadata is None:
        raise Exception("not a valid json file: %s" % metadata_file_path)

    service = get_record_service()
    draft = service.create(identity=identity, data=metadata)
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
