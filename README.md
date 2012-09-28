collectd-eucalyptus
===================

A Eucalyptus plugin for collectd using collectd's Python plugin.

Data captured includes:
  - Instances by instance type
  - Total instances available in cluster by instance type
  - Max instances available in cluster by instance type


Install
-------
 1. Place instance_info.py in /opt/collectd/etc/plugins.d (assuming you have collectd installed to /opt/collectd).
 2. Configure the plugin (see below).
 3. Restart collectd.

Configuration
-------------
Add the following to your collectd config 

    <LoadPlugin python>
      Globals true
    </LoadPlugin>

    <Plugin python>
      ModulePath "/opt/collectd/etc/plugins.d/"
      LogTraces true
      Interactive false
      Import "instance_info"

      <Module instance_info>
         Host "CLC Server"
         AccessKey "AccessKey available in eucarc"
         SecretKey "SecretKey available in eucarc"
         ApiVersion "2009-11-30"
       </Module>
     </Plugin>

Requirements
------------
 * collectd 4.9+

Dont forget to test your plugins by running :
 collectd -C  etc/collectd.conf -T 

If this causes nothing to be printed on the STDOUT, that means your plugins are good.
