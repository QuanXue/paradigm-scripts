#!/usr/bin/env python
"""
galaxyParadigm.py
    by Sam Ng, Steve Benz, Charles Vaske, and Kyle Ellrott
"""
import glob, logging, os, re, resource, shutil, sys, zipfile

from optparse import OptionParser
from jobTree.scriptTree.target import Target
from jobTree.scriptTree.stack import Stack

## logger
logging.basicConfig(filename="paradigm.log", level=logging.INFO)

## executabes
bin_dir = os.path.dirname(os.path.abspath(__file__))
prepare_exec = os.path.join(bin_dir, "prepareParadigm.py")
paradigm_exec = os.path.join(bin_dir, "paradigm")
collect_exec = os.path.join(bin_dir, "collectParameters")
batch_exec = os.path.join(bin_dir, "mergeSwarmFiles.py")
merge_exec = os.path.join(bin_dir, "merge_merged.py")
filter_exec = os.path.join(bin_dir, "filterFeatures.py")

## defaults
standard_dogma = os.path.join(bin_dir, "standard.dogma")
standard_pathway = os.path.join(bin_dir, "pid_110725_pathway.tab")
standard_inference = "method=BP,updates=SEQFIX,tol=1e-9,maxiter=1,logdomain=0"

## gp functions
def commandAvailable(executable):
    return(os.system("which %s > /dev/null 2> /dev/null" % executable) == 0)

def zipDirectory(directory, zip):
    for root, dirs, files in os.walk(directory):
        for file in files:
            zip.write(os.path.join(root, file))

## jt classes
class ParadigmCommand(Target):
    def __init__(self, command, directory):
        Target.__init__(self, time=1000)
        self.command = command
        self.directory = directory
    def run(self):
        os.chdir(self.directory)
        
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.system(self.command)

class PrepareParadigm(Target):
    def __init__(self, evidence_spec, disc, param_file, null_size, paradigm_exec, inference_spec, dogma_lib, pathway_lib, run_em, directory, paradigm_public):
        Target.__init__(self, time=10000)
        self.evidence_spec = evidence_spec
        self.disc = disc
        self.param_file = param_file
        self.null_size = null_size
        self.paradigm_exec = paradigm_exec
        self.inference_spec = inference_spec
        self.dogma_lib = dogma_lib
        self.pathway_lib = pathway_lib
        self.run_em = run_em
        self.directory = directory
        self.paradigm_public = paradigm_public
    def run(self):
        os.chdir(self.directory)
        
        if os.path.exists('clusterFiles/'):
            assert os.path.exists("jobs.list")
            assert os.path.exists("jobsEM.list")
            assert os.path.exists("config.txt")
            assert os.path.exists("configEM.txt")
            assert os.path.exists("params0.txt")
        else:
            optional_flags = " "
            if self.paradigm_public:
                optional_flags += "-y "
            if self.param_file is not None:
                optional_flags += "-t %s " % (self.param_file)
            cmd = "%s %s%s -b \"%s\" -s same -n %s -i %s -e %s -d %s -p %s %s" \
                                                                % (sys.executable,
                                                                   prepare_exec,
                                                                   optional_flags,
                                                                   self.disc,
                                                                   self.null_size,
                                                                   self.inference_spec,
                                                                   self.paradigm_exec,
                                                                   self.dogma_lib,
                                                                   self.pathway_lib,
                                                                   self.evidence_spec)
            l = open("prepare.log", "w")
            l.write(cmd)
            l.close()
            os.system(cmd)
        if self.run_em:
            self.setFollowOnTarget(ExpectationIteration(0, 0.001, self.directory))
        else:
            self.setFollowOnTarget(FinalRun(0, self.directory))

class MaximizationIteration(Target):
    def __init__(self, iteration, tolerance, directory):
        Target.__init__(self, time=10000)
        self.iteration = iteration
        self.tolerance = tolerance
        self.directory = directory
    def readLL(self, filename):
        f = open(filename, "r")
        topline = f.readline().rstrip()
        f.close()
        m = re.search("logZ=([0-9.e+-]*)", topline)
        return float(m.group(1))
    def emHasTerminated(self):
        if self.iteration < 2:
            return False
        prevLL = self.readLL("params%i.txt" % (self.iteration - 1))
        currLL = self.readLL("params%i.txt" % (self.iteration))
        decrease = ((prevLL - currLL) / currLL)
        logging.info("LL: %5g, Decrease: %3g" % (currLL, 100*decrease))
        return decrease < self.tolerance
    def run(self):
        os.chdir(self.directory)
        
        cmd = "%s -p outputFilesEM/*learn* " % (collect_exec)
        if (os.path.exists("mask.expectations")):
            cmd += " mask.expectations "
        cmd += "| %s -o params%i.txt /dev/stdin " \
                    % (collect_exec, self.iteration + 1)
        if (os.path.exists("mask.params")):
            cmd += " mask.params "
        os.system(cmd)
        if self.emHasTerminated():
            self.setFollowOnTarget(FinalRun(self.iteration + 1, self.directory))
        else:
            self.setFollowOnTarget(ExpectationIteration(self.iteration + 1,
                                                        self.tolerance,
                                                        self.directory))

class ExpectationIteration(Target):
    def __init__(self, iteration, tolerance, directory):
        Target.__init__(self, time=1000)
        self.iteration = iteration
        self.tolerance = tolerance
        self.directory = directory
    def run(self):
        os.chdir(self.directory)
        
        os.system("rm -f params.txt")
        os.system("ln -s params%i.txt params.txt" % self.iteration)
        os.system("mkdir -p outputFilesEM%i" % self.iteration)
        os.system("rm -f outputFilesEM")
        os.system("ln -s outputFilesEM%i outputFilesEM" % self.iteration)
        logging.info("Current directory: %s\n" % (os.getcwd()))
        f = open("jobsEM.list", "r")
        for job in f:
            self.addChildTarget(ParadigmCommand(job, self.directory))
        f.close()
        self.setFollowOnTarget(MaximizationIteration(self.iteration, 
                                                     self.tolerance,
                                                     self.directory))

class FinalRun(Target):
    def __init__(self, iteration, directory):
        Target.__init__(self, time=10000)
        self.iteration = iteration
        self.directory = directory
    def run(self):
        os.chdir(self.directory)
        
        os.system("rm -f params.txt")
        os.system("ln -s params%i.txt params.txt" % self.iteration)
        os.system("mkdir -p outputFiles")
        f = open("jobs.list", "r")
        for job in f:
            self.addChildTarget(ParadigmCommand(job, self.directory))
        f.close()
        self.setFollowOnTarget(Merge(self.directory))

class Merge(Target):
    def __init__(self, directory):
        Target.__init__(self, time=10000)
        self.directory = directory
    def run(self):
        os.chdir(self.directory)
        
        os.system("mkdir -p mergeFiles")
        os.system("%s %s outputFiles mergeFiles" % (sys.executable, batch_exec))
        mergeFiles = glob.glob("mergeFiles/*transpose*")
        if len(mergeFiles) == 1:
            os.system("cat %s | sed 's/ loglikelihood=-[0-9.]*//g' > merge_merged_unfiltered.all.tab" % (mergeFiles[0]))
        else:
            os.system("%s %s bioInt mergeFiles/" % (sys.executable, merge_exec))

def gp_main():
    ## check for fresh run
    if os.path.exists(".jobTree"):
        logging.earning("WARNING: '.jobTree' directory found, remove it first to start a fresh run\n")
    
    ## parse arguments
    parser = OptionParser(usage = "%prog [options] attachment file:path [attachment file:path ...]")
    Stack.addJobTreeOptions(parser)
    parser.add_option("--jobFile",
                      help = "Add as a child of jobFile rather than making a new jobTree")
    parser.add_option("-w", "--workdir", dest = "work_dir", default = "./",
                      help = "Directory to perform work in")
    parser.add_option("-n", "--nulls", dest = "null_size", default="5",
                      help = "Number of null samples to be generated per real sample")
    parser.add_option("-d", "--dogma", dest = "dogma_lib", default = standard_dogma,
                      help = "Directory of PARADIGM Dogma specification")
    parser.add_option("-t", "--param", dest = "param_file", default = None,
                      help = "Path to initial PARADIGM Parameters")
    parser.add_option("-p", "--pathway", dest = "pathway_lib", default=standard_pathway,
                      help = "Path to PARADIGM Pathway (directory/file/zip)")
    parser.add_option("-b", "--boundaries", dest = "disc", default="0.33;0.67",
                      help = "Data discretization boundaries")
    parser.add_option("-s", "--skipem", action = "store_false", dest="run_em", default=True,
                      help = "Skip EM steps")
    parser.add_option("-y", dest = "paradigm_public", action = "store_true", default = False,
                      help = "This flag must be enabled when using the publically available version of paradigm")
    
    parser.add_option("-o", "--output-ipls", dest = "output_ipls", default = "paradigm.ipls",
                      help = "Unfiltered Output")
    parser.add_option("--op", "--output-params", dest = "output_params", default = None,
                      help = "Parameter Output")
    parser.add_option("--oc", "--output-config", dest = "output_config", default = None,
                      help = "Config Output")
    parser.add_option("--of", "--output-files", dest = "output_files", default = None,
                      help = "Output Files")
    
    options, args = parser.parse_args()
    logging.info("options: %s" % (str(options)))
    print "Using Batch System '%s'" % (options.batchSystem)
    
    evidence_list = []
    for i, element in enumerate(args):
        if i % 2 == 1:
            (file_type, file_path) = args[i].split(":")
            evidence_list.append("%s:%s" % (file_type, os.path.abspath(file_path)))
        else:
            evidence_list.append(args[i])
    
    if (len(evidence_list) % 2 == 1) | (len(evidence_list) == 0):
        logging.info("ERROR: incorrect number of arguments\n")
        sys.exit(1)
    
    work_dir = os.path.abspath(options.work_dir)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)
    null_size = int(options.null_size)
    disc = options.disc
    if options.param_file is not None:
        param_file = os.path.abspath(options.param_file)
    else:
        param_file  = None
    run_em = options.run_em
    
    ## import dogma and pathway libraries
    ## handle dogma zip or directory and pathway zip, file, or directory
    dogma_lib = os.path.abspath(options.dogma_lib)
    pathway_lib = os.path.abspath(options.pathway_lib)
    
    ## initialize the stack and run
    logging.info("starting prepare")
    s = Stack(PrepareParadigm(evidence_spec=" ".join(evidence_list),
                              disc = disc,
                              param_file = param_file,
                              null_size = null_size,
                              paradigm_exec = paradigm_exec,
                              inference_spec = standard_inference,
                              dogma_lib = dogma_lib,
                              pathway_lib = pathway_lib,
                              run_em = run_em,
                              directory = work_dir,
                              paradigm_public = options.paradigm_public))
    if options.jobFile:
        s.addToJobFile(options.jobFile)
    else:
        if options.jobTree == None:
            options.jobTree = "./.jobTree"
        
        failed = s.startJobTree(options)
        if failed:
            print ("%d jobs failed" % failed)
        else:
            shutil.copy(os.path.join(options.work_dir, "merge_merged_unfiltered.all.tab"), options.output_ipls)
            if options.output_params is not None:
                shutil.copy(os.path.join(options.work_dir, "params.txt"), options.output_params)
            if options.output_config is not None:
                shutil.copy(os.path.join(options.work_dir, "config.txt"), options.output_config)
            if options.output_files is not None:
                zip_file = zipfile.ZipFile("outputFiles.zip", "w")
                zipDirectory("outputFiles", zip_file)
                zip_file.close()
                shutil.copy(os.path.join(options.work_dir, "outputFiles.zip"), options.output_files)
            
            logging.info("Run complete!")
            if os.path.exists(".lastTree"):
                os.system("rm -rf .lastTree")
            if os.path.exists(".jobTree"):
                os.system("mv .jobTree .lastTree")

if __name__ == "__main__":
    from galaxyParadigm import *
    gp_main()
