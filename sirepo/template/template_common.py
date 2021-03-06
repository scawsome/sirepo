# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp
import copy
import hashlib
import json
import re
import sirepo.template

#: Input json file
INPUT_BASE_NAME = 'in'

#: Output json file
OUTPUT_BASE_NAME = 'out'

#: Python file (not all simulations)
PARAMETERS_PYTHON_FILE = 'parameters.py'

#: stderr and stdout
RUN_LOG = 'run.log'


def flatten_data(d, res, prefix=''):
    """Takes a nested dictionary and converts it to a single level dictionary with flattened keys."""
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = v
    return res


def parse_enums(enum_schema):
    """Returns a list of enum values, keyed by enum name."""
    res = {}
    for k in enum_schema:
        res[k] = {}
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res


def report_parameters_hash(data):
    """Compute a hash of the parameters for his report.

    Only needs to be unique relative to the report, not globally unique
    so MD5 is adequate. Long and cryptographic hashes make the
    cache checks slower.

    Args:
        data (dict): report and related models
    Returns:
        str: url safe encoded hash
    """
    if not 'reportParametersHash' in data:
        models = sirepo.template.import_module(data).models_related_to_report(data)
        #TODO(robnagler) need to eliminate non-models from data['models']
        if not models:
            models = data['models'].keys()
            for k in 'panelState', 'rpnCache', 'simulationStatus', 'simulation':
                if k in models:
                    models.remove(k)
        assert models, \
            '{}: models is empty'.format(data)
        res = hashlib.md5()
        if data['report'] in data['models']:
            models.append(data['report'])
        for m in sorted(models):
            md = data['models'][m]
            if m == 'simulation':
                md = copy.deepcopy(md)
                for k in 'simulationSerial', 'outOfSessionSimulationId', 'simulationId', 'folder', 'documentationUrl', 'facility', 'isExample', 'name':
                    if k in md:
                        del md[k]
            j = json.dumps(md, sort_keys=True)
            res.update(j)
        data['reportParametersHash'] = res.hexdigest()
    return data['reportParametersHash']


def validate_model(model_data, model_schema, enum_info):
    """Ensure the value is valid for the field type. Scales values as needed."""
    for k in model_schema:
        label = model_schema[k][0]
        field_type = model_schema[k][1]
        if k in model_data:
            value = model_data[k]
        elif len(model_schema[k]) > 2:
            value = model_schema[k][2]
        else:
            raise Exception('no value for field "{}" and no default value in schema'.format(k))
        if field_type in enum_info:
            if str(value) not in enum_info[field_type]:
                raise Exception('invalid enum value: {} for {}'.format(value, k))
        elif field_type == 'Float':
            if not value:
                value = 0
            v = float(value)
            if re.search('\[m(m|rad)\]', label):
                v /= 1000
            elif re.search('\[nm\]', label) or re.search('\[nm/pixel\]', label):
                v /= 1e09
            elif re.search('\[ps]', label):
                v /= 1e12
            #TODO(pjm): need to handle unicode in label better (mu)
            elif re.search('\[\xb5(m|rad)\]', label):
                v /= 1e6
            model_data[k] = float(v)
        elif field_type == 'Integer':
            if not value:
                value = 0
            model_data[k] = int(value)
        elif field_type in (
                'BeamList', 'MirrorFile', 'ImageFile', 'String', 'OptionalString', 'MagneticZipFile',
                'ValueList', 'Array', 'InputFile', 'RPNValue', 'OutputFile', 'StringArray',
                'InputFileXY', 'BeamInputFile', 'ElegantBeamlineList', 'ElegantLatticeList',
                'RPNBoolean',
        ):
            model_data[k] = _escape(value)
        else:
            raise Exception('unknown field type: {} for {}'.format(field_type, k))

def _escape(v):
    return re.sub("['()]", '', str(v))
