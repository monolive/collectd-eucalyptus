#!/usr/bin/python
# eucalyptus-collectd-plugin - instance_info.py
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; only version 2 of the License is applicable.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# Authors:
#   Olivier Renault <olivier.renault at eucalyptus.com>
#
# About this plugin:
#   This plugin uses collectd's Python plugin to record Eucalyptus instance information.
#
# collectd:
#   http://collectd.org
# Eucalyptus:
#   http://www.eucalyptus.com
# collectd-python:
#   http://collectd.org/documentation/manpages/collectd-python.5.shtml

import collectd
import socket
import boto
from boto.ec2.regioninfo import RegionInfo


# Host to connect to. Override in config by specifying 'Host'.
CLC_HOST = 'localhost'

# Access key to use. Override in config by specifying 'AccessKey'.
ACCESS_KEY = 'Available within eucarc'

# Secret key to use. Override in config by specifying 'SecretKey'.
SECRET_KEY = 'Available within eucarc'

# API Version. Override in config by specifying 'ApiVersion'.
API_VERSION = '2009-11-30'

# Verbose logging on/off. Override in config by specifying 'Verbose'.
VERBOSE_LOGGING = False

def fetch_info():
    """Connect to Eucalyptus server and request info"""
    try:
        conn = boto.connect_ec2(aws_access_key_id=ACCESS_KEY,
                        aws_secret_access_key=SECRET_KEY,
                        is_secure=False,
                        region=RegionInfo(name="eucalyptus", endpoint=CLC_HOST),
                        port=8773,
                        path="/services/Eucalyptus")
        conn.APIVersion = API_VERSION
        log_verbose('Connected to Eucalytpus at %s' % (CLC_HOST))
    except socket.error, e:
        collectd.error('instance_info plugin: Error connecting to %s - %r'
                       % (CLC_HOST, e))
        return None
    log_verbose('Sending info command')
    instanceType=[]
    for reservation in conn.get_all_instances():
        instanceType.append(reservation.instances[0].instance_type)

    return instanceType


def configure_callback(conf):
    """Receive configuration block"""
    global CLC_HOST, ACCESS_KEY, SECRET_KEY, API_VERSION, VERBOSE_LOGGING
    for node in conf.children:
        if node.key == 'Host':
            CLC_HOST = node.values[0]
        elif node.key == 'AccessKey':
            ACCESS_KEY = node.values[0]
        elif node.key == 'SecretKey':
            SECRET_KEY = node.values[0]
        elif node.key == 'ApiVersion':
            API_VERSION = node.values[0]
        elif node.key == 'Verbose':
            VERBOSE_LOGGING = bool(node.values[0])
        else:
            collectd.warning('instance_info plugin: Unknown config key: %s.'
                             % node.key)
    log_verbose('Configured with host=%s' % (CLC_HOST))


def dispatch_value(info, key, type, type_instance=None):
    """Read a key from info response data and dispatch a value"""
    if not type_instance:
        type_instance = key

    value = int(info)
    log_verbose('Sending value: %s=%s' % (type_instance, value))

    val = collectd.Values(plugin='instance_info')
    val.type = type
    val.type_instance = type_instance
    val.values = [value]
    val.dispatch()


def read_callback():
    log_verbose('Read callback called')
    info = fetch_info()

    if not info:
        collectd.error('Eucalyptus plugin: No info received')
        return

    # send high-level values
    dispatch_value(info.count('m1.small'), 'm1.small','gauge')
    dispatch_value(info.count('c1.medium'), 'c1.medium','gauge')
    dispatch_value(info.count('m1.large'), 'm1.large','gauge')
    dispatch_value(info.count('m1.xlarge'), 'm1.xlarge','gauge')
    dispatch_value(info.count('c1.xlarge'), 'c1.xlarge','gauge')
    

def log_verbose(msg):
    if not VERBOSE_LOGGING:
        return
    collectd.info('Eucalyptus plugin [verbose]: %s' % msg)


# register callbacks
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
