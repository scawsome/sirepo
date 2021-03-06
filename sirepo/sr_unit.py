# -*- coding: utf-8 -*-
u"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkunit, pkio
from sirepo import server
from sirepo import simulation_db
import flask
import flask.testing
import json


def flask_client():
    """Return FlaskClient with easy access methods.

    Creates a new run directory every test file so can assume
    sharing of state on the server within a file (module).

    Two methods of interest: `sr_post` and `sr_get`.

    Returns:
        FlaskClient: for local requests to Flask server
    """
    a = 'sr_unit_flask_client'
    if not hasattr(server.app, a):
        with pkio.save_chdir(pkunit.work_dir()):
            db = pkio.mkdir_parent('db')
            server.app.config['TESTING'] = True
            server.app.test_client_class = _TestClient
            server.init(db)
            setattr(server.app, a, server.app.test_client())
    return getattr(server.app, a)


def test_in_request(op):
    from sirepo import server
    fc = flask_client()
    try:
        setattr(server.app, server.SR_UNIT_TEST_IN_REQUEST, op)
        fc.get(server.SR_UNIT_ROUTE)
    finally:
        delattr(server.app, server.SR_UNIT_TEST_IN_REQUEST)


class _TestClient(flask.testing.FlaskClient):

    def sr_post(self, route_name, data, params=None):
        """Posts a request to route_name to server with data

        Args:
            route_name (str): identifies route in schema-common.json
            data (object): will be formatted as JSON
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, data=json.dumps(data), content_type='application/json')
        return _req(route_name, params, op)


    def sr_get(self, route_name, params=None):
        """Gets a request to route_name to server

        Args:
            route_name (str): identifies route in schema-common.json
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        return _req(route_name, params, self.get)


def _req(route_name, params, op):
    """Make request and parse result

    Args:
        route_name (str): string name of route
        params (dict): parameters to apply to route
        op (func): how to request

    Returns:
        object: parsed JSON result
    """
    resp = op(_route(route_name, params))
    return simulation_db.json_load(resp.data)


def _route(route_name, params):
    """Convert name to uri found in SCHEMA_COMMON.

    Args:
        route_name (str): string name of route
        params (dict): parameters to apply to route

    Returns:
        str: URI
    """
    route = simulation_db.SCHEMA_COMMON['route'][route_name]
    if params:
        for k, v in params.items():
            k2 = '<' + k + '>'
            new_route = route.replace(k2, v)
            assert new_route != route, \
                '{}: not found in "{}"'.format(k2, route)
            route = new_route
    assert not '<' in route, \
        '{}: missing params'.format(route)
    return route
