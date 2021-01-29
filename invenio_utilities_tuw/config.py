# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Some utilities for InvenioRDM."""

from invenio_rdm_records.proxies import current_rdm_records

UTILITIES_TUW_BASE_TEMPLATE = "invenio_utilities_tuw/base.html"
"""Default base template for the demo page."""

UTILITIES_TUW_RECORD_SERVICE_FACTORY = lambda: current_rdm_records.records_service
"""Factory function for creating a RecordService."""

UTILITIES_TUW_RECORD_FILES_SERVICE_FACTORY = (
    lambda: current_rdm_records.record_files_service
)
"""Factory function for creating a RecordFileService."""

UTILITIES_TUW_DRAFT_FILES_SERVICE_FACTORY = (
    lambda: current_rdm_records.draft_files_service
)
"""Factory function for creating a DraftFileService."""
