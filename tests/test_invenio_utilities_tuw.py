# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 TU Wien.
#
# Invenio-Utilities-TUW is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Module tests."""

from flask import Flask

from invenio_utilities_tuw import InvenioUtilitiesTUW


def test_version():
    """Test version import."""
    from invenio_utilities_tuw import __version__

    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask("testapp")
    ext = InvenioUtilitiesTUW(app)
    assert "invenio-utilities-tuw" in app.extensions

    app = Flask("testapp")
    ext = InvenioUtilitiesTUW()
    assert "invenio-utilities-tuw" not in app.extensions
    ext.init_app(app)
    assert "invenio-utilities-tuw" in app.extensions
