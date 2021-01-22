# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Utility functions for Invenio-Utilities-TUW."""


from flask import current_app
from invenio_rdm_records.proxies import current_rdm_records
from werkzeug.utils import import_string


def get_or_import(value, default=None):
    """Try an import if value is an endpoint string, or return value itself."""
    if isinstance(value, str):
        return import_string(value)
    elif value:
        return value

    return default


def get_record_service():
    """Get the configured RecordService."""
    factory = current_app.config.get(
        "UTILITIES_TUW_RECORD_SERVICE_FACTORY",
        lambda: current_rdm_records.records_service,
    )
    return factory()


def get_record_file_service():
    """Get the configured RecordFileService."""
    factory = current_app.config.get(
        "UTILITIES_TUW_RECORD_FILES_SERVICE_FACTORY",
        lambda: current_rdm_records.record_files_service,
    )
    return factory()


def get_draft_file_service():
    """Get the configured DraftFilesService."""
    factory = current_app.config.get(
        "UTILITIES_TUW_DRAFT_FILES_SERVICE_FACTORY",
        lambda: current_rdm_records.draft_files_service,
    )
    return factory()
