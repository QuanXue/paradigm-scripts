#!/usr/bin/env python
"""
jtgalaxyParadigm.py: handles setup and running of paradigm on multiple cohorts and/or pathways
"""
## Written by: Sam Ng
import getopt, os, os.path, re, sys
from optparse import OptionParser
from jtParadigm import *
import shutil

from jobTree.scriptTree.target import Target
from jobTree.scriptTree.stack import Stack

basedir = os.path.dirname(os.path.abspath(__file__))

basedogma = os.path.join(basedir, "d_standard.zip")
basepathway = os.path.join(basedir, "p_global_five3_v2.zip")

paradigmExec = os.path.join(basedir, "paradigm")
prepareExec = os.path.join(basedir, "prepareParadigm.py")
inferSpec = "method=BP,updates=SEQFIX,tol=1e-9,maxiter=%s,logdomain=0"

class prepareParadigm(Target):
    def __init__(self, evidSpec, disc, paramFile, nullBatches, paradigmExec, inferSpec, dogmaLib, pathwayLib, em, directory):
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
    def run(self):
        os.chdir(self.directory)
        if self.paramFile is not None:
            cmd = "%s %s -b \"%s\" -t %s -s same -n %s -i %s -e %s -d %s -p %s %s " % (sys.executable, prepareExec, self.disc, self.paramFile, self.nullBatches, self.inferSpec, self.paradigmExec, self.dogmaLib, self.pathwayLib, self.evidSpec)
        else:
            cmd = "%s %s -b \"%s\" -s same -n %s -i %s -e %s -d %s -p %s %s " % (sys.executable, prepareExec, self.disc, self.nullBatches, self.inferSpec, self.paradigmExec, self.dogmaLib, self.pathwayLib, self.evidSpec)
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
    parser.add_option("-d", "--dogma", dest="dogmazip", help="Path to PARADIGM Dogma Specification", default=basedogma)
    parser.add_option("-p", "--pathway", dest="pathwayzip", help="Path to PARADIGM Pathway Specification", default=basepathway)
    parser.add_option("-b", "--boundaries", dest="disc", help="Data Discretization Bounds", default="0.33;0.67")
    parser.add_option("-t", "--storedparam", dest="param", help="Initial Parameter Starting Point", default=None)
    parser.add_option("-s", "--skipem", action="store_false", dest="em", help="Skip Running EM", default=True)
    parser.add_option("--lb-max", dest="lb_max", help="Loopy Belief Max iterations", default=10000)
    parser.add_option("--fr", "--filter-real", dest="filtered_real", help="Filtered Output", default=None)
    parser.add_option("--fa", "--filter-all", dest="filtered_all", help="Filtered Output", default=None)
    parser.add_option("--ur", "--unfilter-real", dest="unfiltered_real", help="Filtered Output", default=None)
    parser.add_option("--ua", "--unfilter-all", dest="unfiltered_all", help="Filtered Output", default=None)
    
    options, args = parser.parse_args()
    logger.info("options: " + str(options))
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
    dogmaZip=os.path.abspath(options.dogmazip)
    pathwayZip=os.path.abspath(options.pathwayzip)
    disc=options.disc
    paramFile=os.path.abspath(options.param) if options.param is not None else None
    runEM = options.em
    
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    dogmaLib = os.path.join(workdir, "dogma")
    pathwayLib = os.path.join(workdir, "pathway")
    system("unzip -o %s -d %s" % (dogmaZip, dogmaLib))
    system("unzip -o %s -d %s" % (pathwayZip, pathwayLib))

    ## run
    logger.info("starting prepare")
    argSpec = inferSpec % (options.lb_max)
    s = Stack(prepareParadigm(" ".join(evidList), disc, paramFile, nullBatches, paradigmExec, argSpec, dogmaLib, pathwayLib, runEM, workdir))
    if options.jobFile:
        s.addToJobFile(options.jobFile)
    else:
        if options.jobTree == None:
            options.jobTree = "./.jobTree"
        
        failed = s.startJobTree(options)
        if failed:
            print ("%d jobs failed" % failed)
        else:
            if options.filtered_all is not None:
                shutil.copy( os.path.join(options.workdir, "merge_merged.all.tab"), options.filtered_all)
            if options.filtered_real is not None:
                shutil.copy( os.path.join(options.workdir, "merge_merged.tab"), options.filtered_real)
            if options.unfiltered_all is not None:
                shutil.copy( os.path.join(options.workdir, "merge_merged_unfiltered.all.tab"), options.unfiltered_all)
            if options.unfiltered_real is not None:
                shutil.copy( os.path.join(options.workdir, "merge_merged_unfiltered.tab"), options.unfiltered_real)

            logger.info("Run complete!")
            if os.path.exists(".lastjobTree"):
                system("rm -rf .lastjobTree")
            if os.path.exists(".jobTree"):
                system("mv .jobTree .lastjobTree")

if __name__ == "__main__":
    from jtgalaxyParadigm import *
    if os.path.exists(".jobTree"):
        print "WARNING: .jobTree directory already exists"
    wrapParadigm()
