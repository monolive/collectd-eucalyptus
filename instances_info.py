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
from collections import defaultdict


# Host to connect to. Override in config by specifying 'Host'.
CLC_HOST = 'localhost'

# Access key to use. Override in config by specifying 'AccessKey'.
ACCESS_KEY = 'AccessKey available from eucarc'

# Secret key to use. Override in config by specifying 'SecretKey'.
SECRET_KEY = 'SecretKey available from eucarc'

# API Version. Override in config by specifying 'ApiVersion'.
API_VERSION = '2009-11-30'

# Verbose logging on/off. Override in config by specifying 'Verbose'.
VERBOSE_LOGGING = False

def conn_eucalyptus():
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
        return conn
    except socket.error, e:
        collectd.error('instance_info plugin: Error connecting to %s - %r'
                       % (CLC_HOST, e))
        return None

def fetch_instance_info(conn):
    """ Grab info on running instance """
    log_verbose('Sending info command')
    image=[]
    instance_type=[]
    for reservation in conn.get_all_instances():
        for i in range(len(reservation.instances)):
            if reservation.instances[i].state == 'running':
                instance_type.append(reservation.instances[i].instance_type)
                image.append(reservation.instances[i].image_id)

    return (image, instance_type)

def fetch_ip_info(conn):
    """Gather IP information"""
    max_ip=0
    free_ip=0
    for ip in conn.get_all_addresses():
        if  ip.instance_id == 'nobody':
            free_ip = free_ip + 1 
        max_ip = max_ip + 1
    return ( max_ip, free_ip)


def fetch_cloud_info(conn):
    """Gather zone information"""
    zones = conn.get_all_zones('verbose')
    status=[]
    for zone in zones:
        zone_string = '%s\t%s' % (zone.name, zone.state)
        words = zone_string.split()
        if len(words) == 3:
           cluster=words[0]
        if len(words) == 8:
           status.append([words[1], int(words[2]), int(words[4]), cluster])
    return status

def count_items(items):
    """Count instance type / images running"""

    counts = defaultdict(int)
    for item in items:
        counts[item] += 1
    return dict(counts)


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
            collectd.warning('instance_info plugin: Unknown config key: %s.' % node.key)
    log_verbose('Configured with host=%s' % (CLC_HOST))


def dispatch_value(info, key, type, type_instance=None):
    """Read a key from info response data and dispatch a value"""
    if not type_instance:
        type_instance = key

    value = int(info)
    log_verbose('Sending value: %s=%s' % (type_instance, value))

    val = collectd.Values(plugin='instance_info')
    val.type = type
    val.host = 'eucalyptus'
    val.type_instance = type_instance
    val.values = [value]
    val.dispatch()


def read_callback():
    log_verbose('Read callback called')
    """Establishing connection"""
    connection = conn_eucalyptus()

    """Getting running instances info"""
    (image, instance_type) = fetch_instance_info(connection)
    if not image and not instance_type:
        collectd.warning('Eucalyptus plugin: No info received, do you have any instances running ?')
        return
    image = count_items(image)
    instance_type = count_items(instance_type)
    if not 'm1.small' in instance_type:
        instance_type['m1.small'] = 0 
    if not 'c1.medium' in instance_type:
        instance_type['c1.medium'] = 0 
    if not 'm1.large' in instance_type:
        instance_type['m1.large'] = 0 
    if not 'm1.xlarge' in instance_type:
        instance_type['m1.xlarge'] = 0 
    if not 'c1.xlarge' in instance_type:
        instance_type['c1.xlarge'] = 0 
    for type in instance_type.keys():
        dispatch_value(instance_type[type], type, 'gauge')
    for emi in image.keys():
        dispatch_value(image[emi], emi, 'gauge' )

    """Getting cloud capacity"""
    status = fetch_cloud_info(connection)
    if not status:
        collectd.warning('Eucalyptus plugin: No Cloud info received, check output of euca-describe-availability-zones verbose')
        return
    for info in range(len(status)):
        dispatch_value(status[info][1],'%s_available_instance_%s' % (status[info][3],  status[info][0]), 'gauge')
        dispatch_value(status[info][2],'%s_max_instance_%s' % (status[info][3], status[info][0]), 'gauge')

    """Getting IP capacity"""
    (max_ip, free_ip) = fetch_ip_info(connection)
    if not max_ip and not free_ip:
        collectd.warning('Eucalyptus plugin: No Cloud info received, check output of euca-describe-availability-zones verbose')
        return
    dispatch_value(max_ip,'max_ip_available','gauge')
    dispatch_value(free_ip,'ip_available','gauge')

def log_verbose(msg):
    if not VERBOSE_LOGGING:
        return
    collectd.info('Eucalyptus plugin [verbose]: %s' % msg)


# register callbacks
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
