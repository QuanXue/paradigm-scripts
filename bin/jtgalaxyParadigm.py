#!/usr/bin/env python
"""
jtgalaxyParadigm.py: handles setup and running of paradigm on multiple cohorts and/or pathways
"""
## Written by: Sam Ng
import getopt, os, os.path, re, sys
from optparse import OptionParser
from jtParadigm import *
import shutil
import logging

from jobTree.scriptTree.target import Target
from jobTree.scriptTree.stack import Stack

logging.basicConfig(filename="paradigm.log", level=logging.INFO)


basedir = os.path.dirname(os.path.abspath(__file__))

basedogma = os.path.join(basedir, "standard.dogma")
baseimap = os.path.join(basedir, "standard.imap")
baseparams = os.path.join(basedir, "params0.txt")
basepathway = os.path.join(basedir, "pid_110725_pathway.tab")

paradigmExec = os.path.join(basedir, "paradigm")
prepareExec = os.path.join(basedir, "prepareParadigm.py")
inferSpec = "method=BP,updates=SEQFIX,tol=1e-9,maxiter=%s,logdomain=0"

class prepareParadigm(Target):
    def __init__(self, evidSpec, disc, paramFile, nullBatches, paradigmExec, inferSpec, dogmaLib, pathwayLib, em, directory, private_paradigm):
        Target.__init__(self, time=10000)
        self.evidSpec = evidSpec
        self.disc = disc
        self.paramFile = paramFile
        self.nullBatches = nullBatches
        self.paradigmExec = paradigmExec
        self.inferSpec = inferSpec
        self.dogmaLib = dogmaLib
        self.pathwayLib = pathwayLib
        self.em = em
        self.directory = directory
        self.private_paradigm = private_paradigm
        
    def run(self):
        os.chdir(self.directory)
        private_flag = ""
        if self.private_paradigm:
            private_flag = "-z"
        
        if self.paramFile is not None:
            cmd = "%s %s -b \"%s\" -t %s -s same -n %s -i %s -e %s -d %s -p %s %s %s " % (sys.executable, prepareExec, self.disc, self.paramFile, self.nullBatches, self.inferSpec, self.paradigmExec, self.dogmaLib, self.pathwayLib, private_flag, self.evidSpec)
        else:
            cmd = "%s %s -b \"%s\" -s same -n %s -i %s -e %s -d %s -p %s %s %s " % (sys.executable, prepareExec, self.disc, self.nullBatches, self.inferSpec, self.paradigmExec, self.dogmaLib, self.pathwayLib, private_flag, self.evidSpec)
        handle=open("prepare.log", "w")
        handle.write(cmd)
        handle.close()
        system(cmd)
        self.setFollowOnTarget(jtParadigm(self.em, self.directory))

class jtParadigm(Target):
    def __init__(self, em, directory):
        Target.__init__(self, time=10000)
        self.em = em
        self.directory = directory
    def run(self):
        os.chdir(self.directory)
        if self.em:
            self.addChildTarget(ExpectationIteration(0, 0.001, "%s" % (self.directory)))
        else:
            self.addChildTarget(FinalRun(0, "%s" % (self.directory)))

def wrapParadigm():
    ## parse arguments
    parser = OptionParser(usage = "%prog [options] attachment file:path [attachment file:path ...]")
    Stack.addJobTreeOptions(parser)
    parser.add_option("--jobFile", help = "Add as a child of jobFile rather " +
                      "than making a new jobTree")
    parser.add_option("-w", "--workdir", dest="workdir", help="Common Work directory", default="./")
    parser.add_option("-n", "--nulls", dest="nulls", help="Number of Null Samples", default="5")
    parser.add_option("-d", "--dogma", dest="dogma", help="Path to PARADIGM Dogma Specification", default=basedogma)
    parser.add_option("-i", "--imap", dest="imap", help="Path to PARADIGM Interaction Map Specification", default=baseimap)
    parser.add_option("-t", "--param", dest="param", help="Initial Parameter Starting Point", default=baseparams)
    
    parser.add_option("-p", "--pathway", dest="pathway", help="Path to PARADIGM Pathway Specification", default=basepathway)
    parser.add_option("-b", "--boundaries", dest="disc", help="Data Discretization Bounds", default="0.33;0.67")
    parser.add_option("-s", "--skipem", action="store_false", dest="em", help="Skip Running EM", default=True)
    parser.add_option("--lb-max", dest="lb_max", help="Loopy Belief Max iterations", default=10000)
    
    parser.add_option("-o", "--output", dest="output_paradigm", help="Unfiltered Output", default="paradigm.output")
    parser.add_option("--op", "--output-params", dest="output_params", help="Parameter Output", default=None)
    parser.add_option("--oc", "--output-config", dest="output_config", help="Config Output", default=None)
    parser.add_option("--of", "--output-files", dest="output_files", help="Output Files", default=None)

    parser.add_option("-z", dest="private_paradigm", help="This is such bullshit", action="store_true", default=False)

    
    options, args = parser.parse_args()
    logging.info("options: " + str(options))
    print "Using Batch System '" + options.batchSystem + "'"
    
    evidList = []
    for i, element in enumerate(args):
        if i % 2 == 1:
            (fileType, filePath) = args[i].split(":")
            evidList.append("%s:%s" % (fileType, os.path.abspath(filePath)))
        else:
            evidList.append(args[i])
    
    if (len(evidList) % 2 == 1) | (len(evidList) == 0):
        sys.stderr.write("ERROR: incorrect number of arguments\n")
        sys.exit(1)
    
 
    workdir = os.path.abspath(options.workdir)
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    nullBatches = int(options.nulls)
    dogma = os.path.abspath(options.dogma)
    pathway = os.path.abspath(options.pathway)
    imap = os.path.abspath(options.imap)
    params = os.path.abspath(options.param)
    disc=options.disc
    paramFile=os.path.abspath(options.param) 
    runEM = options.em
    
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    dogmaLib = os.path.join(workdir, "dogma")
    pathwayLib = os.path.join(workdir, "pathway")
    os.makedirs(dogmaLib)
    os.makedirs(pathwayLib)
    shutil.copy(dogma, dogmaLib)
    shutil.copy(imap, dogmaLib)
    shutil.copy(pathway, pathwayLib)


    ## run
    logging.info("starting prepare")
    argSpec = inferSpec % (options.lb_max)
    s = Stack(prepareParadigm(evidSpec=" ".join(evidList), disc=disc, 
        paramFile=paramFile, nullBatches=nullBatches, 
        paradigmExec=paradigmExec, inferSpec=argSpec, 
        dogmaLib=dogmaLib, pathwayLib=pathwayLib, em=runEM, directory=workdir,
        private_paradigm=options.private_paradigm
        ))
    if options.jobFile:
        s.addToJobFile(options.jobFile)
    else:
        if options.jobTree == None:
            options.jobTree = "./.jobTree"
        
        failed = s.startJobTree(options)
        if failed:
            print ("%d jobs failed" % failed)
        else:
            shutil.copy( os.path.join(options.workdir, "merge_merged_unfiltered.all.tab"), options.output_paradigm)
            if options.output_params is not None:
                shutil.copy( os.path.join(options.workdir, "params.txt"), options.output_params)
            if options.output_config is not None:
                shutil.copy( os.path.join(options.workdir, "config.txt"), options.output_config)
            if options.output_files is not None:
                system("zip -r outputFiles.zip outputFiles")
                shutil.copy( os.path.join(options.workdir, "outputFiles.zip"), options.output_files)
                
            logging.info("Run complete!")
            if os.path.exists(".lastjobTree"):
                system("rm -rf .lastjobTree")
            if os.path.exists(".jobTree"):
                system("mv .jobTree .lastjobTree")

if __name__ == "__main__":
    from jtgalaxyParadigm import *
    if os.path.exists(".jobTree"):
        print "WARNING: .jobTree directory already exists"
    wrapParadigm()
