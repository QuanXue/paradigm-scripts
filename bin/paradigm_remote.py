#!/usr/bin/env python

"""

paradigm_remote

This script uses ssh to execute a paradigm job on a remote-node

It uses a config file to deterime the various parameters needed for running 
remotely.
Example config file:


[REMOTE]

SERVER = ku.sdsc.edu
INSTALL = /cluster/home/ubuntu/paradigm
WORKBASE = /cluster/home/ubuntu/paradigm_remote_work
PYTHON = /cluster/home/ubuntu/bin/python2.7
PYTHONPATH = /cluster/home/ubuntu/paradigm
USER = baertsch


"""


import sys
import subprocess
import uuid
import os
from optparse import OptionParser
import ConfigParser

PARADIGM_EXE = "jtgalaxyParadigm.py"
#PARADIGM_EXE = "paradigm_mock.py"


def remote_cmd(cmd):
    ssh_cmd_base = [ 'ssh', '-o', "ServerAliveInterval=60", '-o', "User="+config.get('REMOTE','USER'),  config.get('REMOTE', 'SERVER') ]
    print "cmd_base", ssh_cmd_base
    print "cmd", cmd
    p = subprocess.Popen( ssh_cmd_base +  cmd )    
    p.communicate()
    if p.returncode:
        raise Exception("Remote Communication Failure")

def remote_put(local, remote):
    ssh_cmd_base = ['scp', '-o', "User="+config.get('REMOTE','USER'), local, config.get('REMOTE', 'SERVER')+ ":" + remote]
    print "put:", " ".join(ssh_cmd_base)
    p = subprocess.Popen( ssh_cmd_base )    
    p.communicate()
    if p.returncode:
        raise Exception("Remote Communication Failure")


def remote_get(local, remote):
    ssh_cmd_base = ['scp', '-o', "User="+config.get('REMOTE','USER'), config.get('REMOTE', 'SERVER') + ":" + remote, local]
    print "get:", " ".join(ssh_cmd_base)
    p = subprocess.Popen( ssh_cmd_base )    
    p.communicate()
    if p.returncode:
        raise Exception("Remote Communication Failure")

if __name__ == "__main__":    
    parser = OptionParser(usage = "%prog [options] attachment file:path [attachment file:path ...]")
    parser.add_option("-w", "--workdir", dest="workdir", help="Common Work directory", default="./")
    parser.add_option("-n", "--nulls", dest="nulls", help="Number of Null Samples", default="5")
    parser.add_option("-d", "--dogma", dest="dogmazip", help="Path to PARADIGM Dogma Specification", default=None)
    parser.add_option("-p", "--pathway", dest="pathway", help="Path to PARADIGM Pathway Specification", default=None)
    parser.add_option("-b", "--boundaries", dest="disc", help="Data Discretization Bounds", default="0.33;0.67")
    parser.add_option("-t", "--storedparam", dest="param", help="Initial Parameter Starting Point", default=None)
    parser.add_option("-s", "--skipem", action="store_false", dest="em", help="Skip Running EM", default=True)
    parser.add_option("-z", "--private-paradigm", action="store_false", dest="private", help="run priveate paradigm", default=True)
    parser.add_option("-l", "--lb-max", dest="lb_max", help="max loopy believe iterations ", default=3000)

    parser.add_option("--config", dest="config_file", help="Filtered Output", default=None)
    
    parser.add_option("--fr", "--filter-real", dest="filtered_real", help="Filtered Output", default=None)
    parser.add_option("--fa", "--filter-all", dest="filtered_all", help="Filtered Output", default=None)
    parser.add_option("--ur", "--unfilter-real", dest="unfiltered_real", help="Filtered Output", default=None)
    parser.add_option("-o", "--unfilter-all", dest="unfiltered_all", help="UnFiltered Output", default=None)
    parser.add_option("--op", "--output-params", dest="output_params", help="Parameter Output", default=None)
    parser.add_option("--oc", "--output-config", dest="output_config", help="Config Output", default=None)
    parser.add_option("--of", "--output-files", dest="output_files", help="Output Files", default=None)
    
    options, args = parser.parse_args()

#    if (len(args) % 2 == 1) | (len(args) == 0):
#        sys.stderr.write("ERROR: incorrect number of arguments\n")
#        sys.exit(1)
    
    if options.config_file is None:
        sys.stderr.write("ERROR: Need Remote config file\n")
        sys.exit(1)
    
    config=ConfigParser.ConfigParser()
    config.read(options.config_file)
        
    evidList = {}
    print args
    for i in range(0,len(args),2):
        (fileType, filePath) = args[i+1].split(":")
        evidList[args[i]] = os.path.abspath(filePath)
    
    remote_id = str(uuid.uuid4())
    remote_dir = os.path.join(config.get('REMOTE', 'WORKBASE'), remote_id)
    remote_cmd([ "mkdir", remote_dir ])
    
    work_dir = os.path.join(remote_dir, "work")
    remote_cmd([ "mkdir", work_dir ])
    
    output_map = {}
    if options.output_params is not None:
        rmt_path = os.path.join(work_dir, os.path.basename(options.output_params))
        output_map[ "--op" ] = (options.output_params, rmt_path)

    if options.output_config is not None:
        rmt_path = os.path.join(work_dir, os.path.basename(options.output_config))
        output_map[ "--oc" ] = (options.output_config, rmt_path)

    if options.output_files is not None:
        rmt_path = os.path.join(work_dir, os.path.basename(options.output_files))
        output_map[ "--of" ] = (options.output_files, rmt_path)

    if options.unfiltered_all is not None:
        rmt_path = os.path.join(work_dir, os.path.basename(options.unfiltered_all))
        output_map[ "-o" ] = (options.unfiltered_all, rmt_path)
   
    
    remote_evid = []
    for e in evidList:
        r_path = os.path.join( remote_dir, os.path.basename(evidList[e]))
        remote_put( evidList[e], r_path)
        remote_evid.append(e)
        remote_evid.append("file:" + r_path)

    if options.pathway is not None:
        p_path = os.path.join( remote_dir, os.path.basename(options.pathway))
        remote_put( options.pathway, p_path)
    
    if options.pathway is not None:
        remote_paradigm_cmd = [ "export PYTHONPATH=" + config.get('REMOTE', 'PYTHONPATH'), "&&", 
            config.get('REMOTE', 'PYTHON'), 
            os.path.join(config.get('REMOTE', 'INSTALL'), PARADIGM_EXE), 
            "--jobTree", os.path.join( remote_dir, "jobTree" ),
            "-p", p_path,
            "-w", work_dir, "-z" ]
    else:
        remote_paradigm_cmd = [ "export PYTHONPATH=" + config.get('REMOTE', 'PYTHONPATH'), "&&", 
            config.get('REMOTE', 'PYTHON'), 
            os.path.join(config.get('REMOTE', 'INSTALL'), PARADIGM_EXE), 
            "--jobTree", os.path.join( remote_dir, "jobTree" ),
            "-w", work_dir, "-z" ]
    
    for o_type in output_map:
        remote_paradigm_cmd += [ o_type, output_map[o_type][1] ]
    
    remote_paradigm_cmd += remote_evid
    print "cmd:", remote_paradigm_cmd
    remote_cmd(remote_paradigm_cmd)
    
    for o_type in output_map:
        remote_get(output_map[o_type][0], output_map[o_type][1])

   



