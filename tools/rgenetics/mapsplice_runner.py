 #    
 #    mapsplice_segments.py	
 #    MapSplice
 #
 #    Copyright (C) 2010 University of Kentucky and
 #                       Kai Wang
 #
 #    Authors: Kai Wang
 #
 #    This program is free software: you can redistribute it and/or modify
 #    it under the terms of the GNU General Public License as published by
 #    the Free Software Foundation, either version 3 of the License, or
 #    (at your option) any later version.
 #
 #    This program is distributed in the hope that it will be useful,
 #    but WITHOUT ANY WARRANTY without even the implied warranty of
 #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 #    GNU General Public License for more details.
 #
 #    You should have received a copy of the GNU General Public License
 #    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 #
 # minor changes by ross lazarus for Galaxy

import sys
import getopt
import subprocess
import errno
import os, glob
import tempfile
import warnings
import shutil
import math
import logging

from datetime import datetime, date, time

                
use_message = '''
Usage:
    mapsplice [Inputs] [options]

Inputs:
    -u/--reads-file                <string>
    -c/--chromosome-files-dir      <string>
    
Options:
    -o/--output-dir                <string>    [ default: ./mapsplice_out ]
    -n/--min-anchor                <int>       [ default: 8               ]
    -m/--splice-mismatches         <int>       [ default: 1               ]
    -i/--min-intron-length         <int>       [ default: 1               ]
    -x/--max-intron-length         <int>       [ default: 50000           ]
    -w/--read-width                <int>       [ default: 100             ]
    -S/--FASTA-files-ext           <string>    [ default: fa              ]
    -G/--numseg                    <int>       [ default: 4               ]
    -L/--seglen                    <int>       [ default: 25              ]
    -B/--Bowtieidx                 <string>
    -Q/--reads-format              <string>    [ default: fq              ]
    --full-running
    -X/--threads                   <int>       [ default: 1               ]
    -E/--segment-mismatches        <int>       [ default: 1               ]
    --pairend
    --search-whole-chromosome
    --map-segments-directly
    --run-MapPER
    --not-rem-temp
    --non-canonical | --semi-canonical
'''

def makeD(d=None):
    """ utility function """
    assert d <> None, '### None passed as directory name to makeD - terminating'
    if not os.path.isdir(d):
        try:
            os.makedirs(d)
        except:
            logging.critical('Unable to create supplied directory %s - terminating' % d)
            logging.shutdown()
            sys.exit(1)


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg
        
output_dir = "mapsplice_out"
logging_dir = os.path.join(output_dir,"logs")
canon_in_intron_dir = os.path.join(output_dir,"canonical")
canon_exceed_intron_dir = os.path.join(output_dir,"canonical_exceed")
noncanon_in_intron_dir = os.path.join(output_dir,"noncanonical")
noncanon_exceed_intron_dir = os.path.join(output_dir,"noncanonical_exceed")
fusion_dir = os.path.join(output_dir,"fusion")
tophat_dir = os.path.join(output_dir,"tophat")
temp_dir = os.path.join(output_dir,"tmp")
original_dir = os.path.join(temp_dir,"original")
filteredbest_dir = os.path.join(temp_dir,"best")
comparison_dir = os.path.join(temp_dir,"comparison")
synthetic_dir = os.path.join(temp_dir,"synthetic")
pairend_dir = os.path.join(temp_dir,"pairend")
remap_dir = os.path.join(temp_dir,"remap")
remap_regions_dir = os.path.join(temp_dir,"remap_regions")
hmer_dir = os.path.join(temp_dir,"single_anchored_middle")
hole_dir = os.path.join(temp_dir,"double_anchored")
head_dir = os.path.join(temp_dir,"single_anchored_head")
tail_dir = os.path.join(temp_dir,"single_anchored_tail")
bwtout_dir = os.path.join(temp_dir,"bwtout")
sam_dir = os.path.join(temp_dir,"sam")
fusion_dir = os.path.join(temp_dir,"fusion")
cluster_dir = os.path.join(temp_dir,"cluster")
cluster_result_dir = os.path.join(cluster_dir,"result")
cluster_data_dir = os.path.join(cluster_dir,"data")
cluster_data_parsedPER_dir = os.path.join(cluster_data_dir,"parsedPER")
fusion_data_dir = os.path.join(fusion_dir,"data")
fusion_data_single_dir = os.path.join(fusion_data_dir,"single")
fusion_data_PER_dir = os.path.join(fusion_data_dir,"PER")
fusion_result_dir = os.path.join(fusion_dir,"result")
fusion_result_PER_prob_dir = os.path.join(fusion_result_dir,"PER_prob")
fusion_result_fusionRead_dir = os.path.join(fusion_result_dir,"fusionRead")
fusion_result_junction_support_dir = os.path.join(fusion_result_dir,"junction_support")
formated_chrom_dir = os.path.join(temp_dir,"formated_chrom")
formated_reads_dir = os.path.join(temp_dir,"formated_reads")
bin_dir = sys.path[0]
rerun_all = 1
DEBUG = 0
fail_str = "\t[FAILED]\n"

class Params:
    
    def __init__(self): 
        self.min_anchor_length = 8
        self.seed_length = 10
        self.splice_mismatches = 1
        self.segment_mismatches = 1
        self.FASTA_file_extension = "fa"
        self.read_file_suffix = "txt"
        self.min_intron_length = 10
        self.max_intron_length = 200000
        self.island_extension = 0
        self.read_width = 0
        self.rank = 0.0
        self.flank_case = 5
        self.islands_file = ""
        self.read_files_dir = ""
        self.chromosome_files_dir = ""
        self.all_chromosomes_file = ""
        self.repeat_regioins = ""
        self.gene_regions = ""
        self.bwt_idx_prefix = ""
        self.bowtie_threads = 1
        self.max_hits = 4
        self.threshold = 1
        self.boundary = 50
        self.num_anchor = 1        
        self.unmapped_reads = ""
        self.sam_formatted = ""
        self.bam_formatted = ""
        self.sam_formatted_25 = ""
        self.bwt_map_25 = ""
        self.pileup_file = ""
        self.synthetic_mappedreads = ""
        self.tophat_mappedreads = ""
        self.pairend = ""
        self.gamma = 0.1
        self.delta = 0.1	
        self.seg_len = 25
        self.fix_hole_file = ""         
        self.format_flag = ""        
        self.chrom_size_file = ""        
        self.bam_file = ""        
        self.extend_bits = 3        
        self.total_fusion_mismatch = 2        
        self.total_mismatch = 2
        self.append_mismatch = 2
        self.remap_mismatch = 2
        self.skip_bwt = 0
        self.prefix_match = 1
        self.fullrunning = 0
        self.collect_stat = 0
        self.rm_temp = 1
        self.format_reads = 0
        self.format_chromos = 0
        self.do_fusion = 0
        self.do_cluster = 0
        self.search_whole_chromo = 0
        self.map_segment_directly = 0
        self.run_mapper = 0
        self.max_insert = 3
        self.min_missed_seg = 0
        self.fusion_flank_case = 5
        self.do_annot_gene = 0
        self.annot_gene_file = ""        
        self.filter_fusion_by_repeat = 0
        self.chromosome_blat_idx = "" 
             


    def fixOutputs(self,output_dir=None):
        makeme = []
        self.output_dir = output_dir
        makeD(self.output_dir)
        self.logging_dir = os.path.join(self.output_dir,"logs")
        makeD(self.logging_dir)
        self.canon_in_intron_dir = os.path.join(self.output_dir,"canonical")
        makeD(self.logging_dir)
        self.canon_exceed_intron_dir = os.path.join(self.output_dir,"canonical_exceed")
        makeD(self.logging_dir)
        self.noncanon_in_intron_dir = os.path.join(self.output_dir,"noncanonical")
        makeD(self.logging_dir)
        self.noncanon_exceed_intron_dir = os.path.join(self.output_dir,"noncanonical_exceed")
        makeD(self.logging_dir)
        self.fusion_dir = os.path.join(self.output_dir,"fusion")
        makeD(self.logging_dir)
        self.tophat_dir = os.path.join(self.output_dir,"tophat")
        makeD(self.logging_dir)
        self.temp_dir = os.path.join(self.output_dir,"tmp")
        makeD(self.logging_dir)
        self.original_dir = os.path.join(self.temp_dir,"original")
        makeD(self.logging_dir)
        self.filteredbest_dir = os.path.join(self.temp_dir,"best")
        makeD(self.logging_dir)
        self.comparison_dir = os.path.join(self.temp_dir,"comparison")
        makeD(self.logging_dir)
        self.synthetic_dir = os.path.join(self.temp_dir,"synthetic")
        makeD(self.logging_dir)
        self.pairend_dir = os.path.join(self.temp_dir,"pairend")
        makeD(self.logging_dir)
        self.remap_dir = os.path.join(self.temp_dir,"remap")
        makeD(self.logging_dir)
        self.remap_regions_dir = os.path.join(self.temp_dir,"remap_regions")
        makeD(self.logging_dir)
        self.hmer_dir = os.path.join(self.temp_dir,"single_anchored_middle")
        makeD(self.logging_dir)
        self.hole_dir = os.path.join(self.temp_dir,"double_anchored")
        makeD(self.logging_dir)
        self.head_dir = os.path.join(self.temp_dir,"single_anchored_head")
        makeD(self.logging_dir)
        self.tail_dir = os.path.join(self.temp_dir,"single_anchored_tail")
        makeD(self.logging_dir)
        self.bwtout_dir = os.path.join(self.temp_dir,"bwtout")
        makeD(self.logging_dir)
        self.sam_dir = os.path.join(self.temp_dir,"sam")
        makeD(self.logging_dir)
        self.fusion_dir = os.path.join(self.temp_dir,"fusion")
        makeD(self.logging_dir)
        self.cluster_dir = os.path.join(self.temp_dir,"cluster")
        makeD(self.logging_dir)
        self.cluster_result_dir = os.path.join(self.cluster_dir,"result")
        makeD(self.logging_dir)
        self.cluster_data_dir = os.path.join(self.cluster_dir,"data")
        makeD(self.logging_dir)
        self.cluster_data_parsedPER_dir = os.path.join(self.cluster_data_dir,"parsedPER")
        makeD(self.logging_dir)
        self.fusion_data_dir = os.path.join(self.fusion_dir,"data")
        makeD(self.logging_dir)
        self.fusion_data_single_dir = os.path.join(self.fusion_data_dir,"single")
        makeD(self.logging_dir)
        self.fusion_data_PER_dir = os.path.join(self.fusion_data_dir,"PER")
        makeD(self.logging_dir)
        self.fusion_result_dir = os.path.join(self.fusion_dir,"result")
        makeD(self.logging_dir)
        self.fusion_result_PER_prob_dir = os.path.join(self.fusion_result_dir,"PER_prob")
        makeD(self.logging_dir)
        self.fusion_result_fusionRead_dir = os.path.join(self.fusion_result_dir,"fusionRead")
        makeD( self.fusion_result_fusionRead_dir)
        self.fusion_result_junction_support_dir = os.path.join(self.fusion_result_dir,"junction_support")
        makeD(self.fusion_result_junction_support_dir)
        self.formated_chrom_dir = os.path.join(self.temp_dir,"formated_chrom")
        makeD(self.formated_chrom_dir)
        self.formated_reads_dir = os.path.join(self.temp_dir,"formated_reads")
        makeD(self.formated_reads_dir)
        self.rm_temp = 0 # defaults
        self.format_flag = '-q'	        
        self.pairend = ''
        self.fullrunning = 0
        self.search_whole_chromo = 0
        self.do_cluster = 0
        self.map_segment_directly = 0
        self.run_mapper = 0   
        self.do_fusion = 0       
        self.comments = [] 
        
        
    def parse_cfgfile(self, cfg_file):
        fh = open(cfg_file,"r")
        igot = fh.readlines()	
        for line in igot:
            line = line.replace(' ','')
            line = line.lower() # avoid case problems
            if not len(line) > 0:
                continue
            if line.startswith('#'):
                self.comments.append(line)
                continue
            command = line.split('=')
            if command == 'output_dir':
                self.fixOutputs(output_dir=command[1])		
            elif command[0] == 'reads_file':
                self.read_files_dir = command[1]
            elif command[0] == 'sam_file':
                self.sam_formatted = command[1]
            elif command[0] == 'chromosome_files_dir':
                self.chromosome_files_dir = command[1]
            elif command[0] == 'Bowtieidx':
                self.bwt_idx_prefix = command[1]
            elif command[0] == 'avoid_regions':
                self.repeat_regioins = command[1]
            elif command[0] == 'interested_regions':
                self.gene_regions = command[1]
            elif command[0] == 'reads_format':
                if command[1] == 'FASTA':
                    self.format_flag = '-f'	
            elif command[0] == 'segment_mismatches':
                self.segment_mismatches = int(command[1])
            elif command[0] == 'segment_length':
                self.seg_len = int(command[1])
            elif command[0] == 'read_length':
                self.read_width = int(command[1])
            elif command[0] == 'paired_end':
                if command[1] == 'yes':
                    self.pairend = '1'
            elif command[0] == 'junction_type':
                if command[1] == 'non-canonical':
                    self.flank_case = 0
                elif command[1] == 'semi-canonical':
                    self.flank_case = 1
                elif command[1] == 'canonical':
                    self.flank_case = 5
            elif command[0] == 'fusion_junction_type':
                if command[1] == 'non-canonical':
                    self.fusion_flank_case = 0
                elif command[1] == 'semi-canonical':
                    self.fusion_flank_case = 1
                elif command[1] == 'canonical':
                    self.fusion_flank_case = 5		
            elif command[0] == 'full_running':
                if command[1] == 'yes':
                    self.fullrunning = 1
            elif command[0] == 'anchor_length':
                self.min_anchor_length = int(command[1])
            elif command[0] == 'remove_temp_files':
                if command[1] == 'yes':
                    self.rm_temp = 1
            elif command[0] == 'remap_mismatches':
                self.remap_mismatch = int(command[1])
            elif command[0] == 'splice_mismatches':
                self.splice_mismatches = int(command[1])
            elif command[0] == 'min_intron_length':
                self.min_intron_length = int(command[1])
            elif command[0] == 'max_intron_length':
                self.max_intron_length = int(command[1])
            elif command[0] == 'threads':
                self.bowtie_threads = int(command[1])
            elif command[0] == 'search_whole_chromosome':
                if command[1] == 'yes':
                    self.search_whole_chromo = 1
            elif command[0] == 'map_segment_directly':
                if command[1] == 'yes':
                    self.map_segment_directly = 1
            elif command[0] == 'run_MapPER':
                if command[1] == 'yes':
                    self.run_mapper = 1
            elif command[0] == 'do_fusion':
                if command[1] == 'yes':
                    self.do_fusion = 1
            elif command[0] == 'do_cluster':
                if command[1] == 'yes':
                    self.do_cluster = 1
            elif command[0] == 'max_insert':	
                self.max_insert = int(command[1])
            elif command[0] == 'BAM':	
                self.bam_file = command[1]
            elif command[0] == 'min_missed_seg':	
                self.min_missed_seg = int(command[1])
            elif command[0] == 'max_hits':	
                self.max_hits = int(command[1])
            elif command[0] == 'do_annot_gene':	    
                self.do_annot_gene = 1
                self.annot_gene_file = (command[1])
            elif command[0] == 'filter_fusion_by_repeat':   
                self.chromosome_blat_idx = (command[1])
                self.filter_fusion_by_repeat = 1

def setLogging(logfname='mapsplice.log'):
    """setup a logger - write with eg logging.debug('foo!')
    """
    logdir = os.path.split(logfname)[0]
    if logdir > '':
        if not os.path.isdir(logdir):
            os.makedirs(logdir)
    logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename=logfname,
                filemode='a')

def get_version():
    return "1.15.2"

def right_now():
    curr_time = datetime.now()
    return curr_time.strftime("%c")


def getFiles(path_name=None,globme=None):    
    sequences = []
    if path_name and not os.path.isdir(path_name):
        sequences.append(path_name)
        return sequences
    for infile in glob.glob( os.path.join(path_name,globme) ):
        sequences.append(infile)
    return sequences

def read_sam(path_name): 
    return getFiles(path_name=path_name,globme='*.sam') 

def read_chroms(path_name):
    return getFiles(path_name=path_name,globme='*.fa') 
    
def read_dir_by_suffix(path_name, suffix):
    return getFiles(path_name=path_name,suffix = '*.%s' % suffix)
    
def read_sequence(path_name):
    return ','.join(read_chroms(path_name=path_name))

def read_sequence_by_suffix(path_name, suffix):
    return ','.join(read_dir_by_suffix(path_name=path_name,suffix=suffix))
    
def check_islands(islands_file):
    logging.info("Checking for islands file %s" % islands_file)
    if os.path.isfile(islands_file):
        return islands_file
    else:
        logging.critical("## Error: Could not find islands file %s. Terminating" % (islands_file))
        logging.shutdown()
        sys.exit(1)

def check_mapsplice():
    logging.info("Checking for MapSplice executables")
    if not os.path.isfile("mapsplice") and os.path.isfile("mapsplice_128"):
        logging.critical("Error: Could not find mapsplice executable files")
        logging.shutdown()
        sys.exit(1)

def check_reads_files(reads_files_or_dir):
    logging.info("Checking for reads files or directory")
    if os.path.exists(reads_files_or_dir):
        return reads_files_or_dir
    else:
        logging.critical("Error: Could not find reads files or directory '%s'" % reads_files_or_dir)
        logging.shutdown()
        sys.exit(1)

def check_chromo_files(chromosomes_files_or_dir):
    logging.info("Checking for chromosomes files or directory '%s'" % (chromosomes_files_or_dir))
    if os.path.exists(chromosomes_files_or_dir):
        mapsplice_log = open(logging_dir + "checking_chromosome_file.log", "w")	
        all_chroms_path = read_dir_by_suffix(chromosomes_files_or_dir, "fa")
        merge_sam_cmd = [bin_dir,]
        merge_sam_cmd.append("check_input_files")  
        merge_sam_cmd += all_chroms_path
        try:    
            retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)	   
            if retcode == 2 or retcode == 3:
                return retcode	    
            elif retcode == 0:
                logging.info("Checking for chromosomes files or directory passed")
                return 0
        except OSError, o:
            if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:                
                logging.critical("Error: check_input_files not found on this system")
                logging.shutdown()
                sys.exit(1)	
    else:
        logging.critical("Error: chromosome files %s not found. Terminating" % chromosomes_files_or_dir)
        logging.shutdown()
        sys.exit(1)	
    
def check_allchromo_file(all_chromosomes_file):
    logging.info("Checking for all chromosomes file")
    if os.path.exists(all_chromosomes_file):
        return all_chromosomes_file
    else:
        logging.critical("Error: all chromosome file %s not found. Terminating" % all_chromosomes_files)
        logging.shutdown()
        sys.exit(1)	

def runExt(cmd=[],errString='',logFile=None):
    """ utility factors out running and handling errors 
    """
    assert cmd <> [],'#ERROR: runExt called without a command line list'
    assert stdout <> None, '#ERROR: runExt called without stdout'
    logging.debug('##runExt now running: %s' % ' '.join(cmd))
    if logFile == None:
        logf = os.path.join(params.logging_dir,"mapsplice_run.log")
    else:
        logf = logFile
    if not os.path.isfile(logf): # make or append
        mapsplice_log = open(logf, "w")
    else:
        mapsplice_log = open(logf, "a")
    runbin = os.path.split(cmd[0])[-1] # just the binary part
    try:    
        retcode = subprocess.call(' '.join(cmd), shell=True, stderr=mapsplice_log,stdout=mapsplice_log)        
        if retcode > 0:
            logging.critical("Error: %s" % errString)
            logging.shutdown()
            sys.exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            logging.critical("Error: %s binary not found on this system - please install properly" % runbin)
            logging.shutdown()
            sys.exit(1)
    mapsplice_log.close()


def call_mapsplice(islands_gff, 
        seed_length,
        read_width,
        min_anchor_len,
        splice_mismatches,
        min_intron_length,
        max_intron_length,
        islands_extension,
        flank_case,
        rank,
        FASTA_file_ext,
        reads_files_dir,
        chromosomes_file_dir,
        num_anchor):
    logging.info("Aligning spliced reads")    
    cmd = ""    
    juncfile = os.path.join(params.logging_dir,"junctions.txt")
    if read_width > 64:
        cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
                      "-v", params.output_dir,          # Output dir
                      "-n", str(min_anchor_len), # Anchor length
                      "-m", str(splice_mismatches), # Mismatches allowed in extension
                      "-x", str(max_intron_length), # Maxmimum intron length
                      "-i", str(min_intron_length), # Minimum intron length
                      "-h", str(seed_length), # Seed size for reads
                      "-w", str(read_width), # read width for reads
                      "-p", str(islands_extension), # islands extension
                      "-b", str(350000000), # block size for reading chromosome
                      "-s", FASTA_file_ext, # FASTA file extension
                      "-t", islands_gff, # island location
                      "-u", reads_files_dir, # reads file or directory
                      "-c", chromosomes_file_dir, # chromosomes file or directory
                      "-y", str(1), # nothing important
                      "-f", str(flank_case), #if is 1, only output flank string that is not case 0
                      "-R", str(rank)   #only output rank >= rank
                      ]
    else:
        cmd = [os.path.join(params.bin_dir,"mapsplice"),
                      "-v", params.output_dir,          # Output dir
                      "-n", str(min_anchor_len), # Anchor length
                      "-m", str(splice_mismatches), # Mismatches allowed in extension
                      "-x", str(max_intron_length), # Maxmimum intron length
                      "-i", str(min_intron_length), # Minimum intron length
                      "-h", str(seed_length), # Seed size for reads
                      "-w", str(read_width), # read width for reads
                      "-p", str(islands_extension), # islands extension
                      "-b", str(350000000), # block size for reading chromosome
                      "-s", FASTA_file_ext, # FASTA file extension
                      "-t", islands_gff, # island location
                      "-u", reads_files_dir, # reads file or directory
                      "-c", chromosomes_file_dir, # chromosomes file or directory
                      "-y", str(1), # nothing important
                      "-f", str(flank_case), #if is 1, only output flank string that is not case 0
                      "-A", str(num_anchor), #number of anchors
                      "-R", str(rank)   #only output rank >= rank
                      ]
    runExt(cmd=cmd,errString='Spliced read alignment failed') 
    return juncfile


def call_mapsplice_segment2(islands_gff, 
        seed_length,
        read_width,
        min_anchor_len,
        splice_mismatches,
        min_intron_length,
        max_intron_length,
        islands_extension,
        flank_case,
        FASTA_file_ext,
        chromosomes_file_dir,
        num_anchor,
        num_seg,
        seg_len,
        bwtout_25,
        cur_ouput_dir,
        extend_bits,
        tmp_dir):
    
    logging.info("Aligning spliced reads")    
    cmd = "" 
    test_file =  os.path.join(params.hmer_dir,"chrX.txt.fixed")
    if os.path.exists(test_file) and params.rerun_all == 0:
        return test_file
    if read_width > 36:
        cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
        "-v", cur_ouput_dir,          # Output dir
        "-n", str(min_anchor_len), # Anchor length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-x", str(max_intron_length), # Maxmimum intron length
        "-i", str(min_intron_length), # Minimum intron length
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-p", str(islands_extension), # islands extension
        "-b", str(350000000), # block size for reading chromosome
        #"-s", FASTA_file_ext, # FASTA file extension
        "-t", islands_gff, # island location
        "-c", chromosomes_file_dir, # chromosomes file or directory
        "-f", str(flank_case), #if is 1, only output flank string that is not case 0
        #"-A", str(num_anchor), #number of anchors
        "-bwtout", bwtout_25, #bwt segment output
        "-G", str(num_seg), #number of segments
        "-L", str(seg_len), #segment length
        #"-E", str(extend_bits), #extend bits when fix hole and fusion
        "-tmp", params.tmp_dir #tmp dir
        ]

    else:
        cmd = [os.path.join(params.bin_dir,"mapsplice"),
        "-v", cur_ouput_dir,          # Output dir
        "-n", str(min_anchor_len), # Anchor length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-x", str(max_intron_length), # Maxmimum intron length
        "-i", str(min_intron_length), # Minimum intron length
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-p", str(islands_extension), # islands extension
        "-b", str(350000000), # block size for reading chromosome
        "-s", FASTA_file_ext, # FASTA file extension
        "-t", islands_gff, # island location
        "-u", reads_files_dir, # reads file or directory
        "-c", chromosomes_file_dir, # chromosomes file or directory
        "-y", str(1), # nothing important
        "-f", str(flank_case), #if is 1, only output flank string that is not case 0
        "-A", str(num_anchor), #number of anchors
        "-R", str(rank)   #only output rank >= rank
        ]
    runExt(cmd=cmd,errString='Spliced read alignment failed') 
  

def call_mapsplice_segment(islands_gff, 
        seed_length,
        read_width,
        min_anchor_len,
        splice_mismatches,
        min_intron_length,
        max_intron_length,
        islands_extension,
        flank_case,
        rank,
        FASTA_file_ext,
        reads_files_dir,
        chromosomes_file_dir,
        num_anchor,
        num_seg,
        seg_len,
        bwtout_25,
        fix_hole_file,
        cur_ouput_dir,
        fqreads,
        extend_bits,
        total_mismatch,
        total_fusion_mismatch,
        append_mismatch,
        prefix_match,
        threads,
        search_whole_chromo,
        max_insert):
    start_time = datetime.now()
    logging.info("Aligning spliced read segments")    
    cmd = ""
    juncfile = os.path.join(params.original_dir,"canonical_junctions.txt")
    fqreads = ""
    test_file =  os.path.join(params.hmer_dir,"chrX.txt.fixed")
    if os.path.exists(test_file) and params.rerun_all == 0:
        return test_file
    if read_width > 0:	
        if fqreads == "":
            cmd = [os.path.join(params.bin_dir, "mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            #"-t", islands_gff, # island location
            #"-u", reads_files_dir, # reads file or directory
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(prefix_match), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            #"-R", str(rank),   #only output rank >= rank
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-max_insertion", str(max_insert), #maximal insert
            "-tmp", params.temp_dir #tmp dir
            ]
        else:
            cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            #"-t", islands_gff, # island location
            #"-u", reads_files_dir, # reads file or directory
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(1), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            #"-R", str(rank),   #only output rank >= rank
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-tmp", params.temp_dir #tmp dir
            #"-FQ", fqreads #fastq reads
            ]
    else:
        cmd = [os.path.join(params.bin_dir,"mapsplice"),
        "-v", cur_ouput_dir,          # Output dir
        "-n", str(min_anchor_len), # Anchor length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-x", str(max_intron_length), # Maxmimum intron length
        "-i", str(min_intron_length), # Minimum intron length
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-p", str(islands_extension), # islands extension
        "-b", str(350000000), # block size for reading chromosome
        "-s", FASTA_file_ext, # FASTA file extension
        "-t", islands_gff, # island location
        "-u", reads_files_dir, # reads file or directory
        "-c", chromosomes_file_dir, # chromosomes file or directory
        "-y", str(1), # nothing important
        "-f", str(flank_case), #if is 1, only output flank string that is not case 0
        "-A", str(num_anchor), #number of anchors
        "-R", str(rank)   #only output rank >= rank
        ]
    if params.search_whole_chromo == 0:
        splice_cmd += ["-t",islands_gff]
    logging.debug("Separating unique and multiple mapped reads using %s" % ' '.join(splice_cmd))    
    runExt(cmd=cmd,errString='Separating unique and multiple mapped reads failed')
    return juncfile

def call_mapsplice_segment_fusion(islands_gff, 
            seed_length,
            read_width,
            min_anchor_len,
            splice_mismatches,
            min_intron_length,
            max_intron_length,
            islands_extension,
            flank_case,
            rank,
            FASTA_file_ext,
            reads_files_dir,
            chromosomes_file_dir,
            num_anchor,
            num_seg,
            seg_len,
            bwtout_25,
            fix_hole_file,
            cur_ouput_dir,
            fqreads,
            extend_bits,
            total_mismatch,
            total_fusion_mismatch,
            append_mismatch,
            prefix_match,
            threads,
            fusion_junction
            ):
    start_time = datetime.now()
    logging.info("Aligning fusion spliced reads")
    cmd = ""
    juncfile = os.path.join(params.original_dir,"canonical_junctions.txt")
    fqreads = ""
    test_file =  fusion_junction
    if os.path.exists(test_file) and params.rerun_all == 0:
        return test_file
    if read_width > 0:
        if fqreads == "":
            cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            "-t", islands_gff, # island location
            #"-u", reads_files_dir, # reads file or directory
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(prefix_match), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            #"-R", str(rank),   #only output rank >= rank
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-tmp", params.temp_dir, #tmp dir
            "-fusion", params.fusion_dir, #fusion dir
            "-fusionjunc", params.fusion_junction #fusion junction
            ]
        else:
            cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            "-t", islands_gff, # island location
            #"-u", reads_files_dir, # reads file or directory
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(1), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            #"-R", str(rank),   #only output rank >= rank
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-tmp", temp_dir, #tmp dir
            "-fusion", fusion_dir,  #fusion dir
            "-fusionjunc", fusion_junction #fusion junction
            #"-FQ", fqreads #fastq reads
            ]
    else:
        cmd = [os.path.join(params.bin_dir,"mapsplice"),
        "-v", cur_ouput_dir,          # Output dir
        "-n", str(min_anchor_len), # Anchor length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-x", str(max_intron_length), # Maxmimum intron length
        "-i", str(min_intron_length), # Minimum intron length
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-p", str(islands_extension), # islands extension
        "-b", str(350000000), # block size for reading chromosome
        "-s", FASTA_file_ext, # FASTA file extension
        "-t", islands_gff, # island location
        "-u", reads_files_dir, # reads file or directory
        "-c", chromosomes_file_dir, # chromosomes file or directory
        "-y", str(1), # nothing important
        "-f", str(flank_case), #if is 1, only output flank string that is not case 0
        "-A", str(num_anchor), #number of anchors
        "-R", str(rank)   #only output rank >= rank
        ]
    logging.debug("separating unique and multiple mapped reads using %s" % ' '.join(splice_cmd))
    runExt(cmd=cmd,errString='Separating unique and multiple mapped reads failed')
    return juncfile

def call_mapsplice_segment_fusion_single_anchor(islands_gff, 
        seed_length,
        read_width,
        min_anchor_len,
        splice_mismatches,
        min_intron_length,
        max_intron_length,
        islands_extension,
        flank_case,
        rank,
        FASTA_file_ext,
        reads_files_dir,
        chromosomes_file_dir,
        num_anchor,
        num_seg,
        seg_len,
        bwtout_25,
        fix_hole_file,
        cur_ouput_dir,
        fqreads,
        extend_bits,
        total_mismatch,
        total_fusion_mismatch,
        append_mismatch,
        prefix_match,
        threads,
        fusion_junction,
        fusion_single_anchor,
        ):
    logging.info("Aligning fusion spliced reads")    
    cmd = ""    
    juncfile = os.path.join(params.original_dir,"canonical_junctions.txt")
    fqreads = ""
    test_file = fusion_junction
    if os.path.exists(test_file) and params.rerun_all == 0:
        return test_file
    if read_width > 0:	
        if fqreads == "":
            cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            "-t", islands_gff, # island location
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(prefix_match), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-tmp", params.temp_dir, #tmp dir
            "-fusion", params.fusion_dir, #fusion dir
            "-fusionjunc", fusion_junction, #fusion junction
            "-fusionsingleanchor", fusion_single_anchor #fusion junction
            ]
        else:
            cmd = [os.path.join(params.bin_dir,"mapsplice_segments"),
            "-v", cur_ouput_dir,          # Output dir
            "-n", str(min_anchor_len), # Anchor length
            "-m", str(splice_mismatches), # Mismatches allowed in extension
            "-x", str(max_intron_length), # Maxmimum intron length
            "-i", str(min_intron_length), # Minimum intron length
            "-h", str(seed_length), # Seed size for reads
            "-w", str(read_width), # read width for reads
            "-p", str(islands_extension), # islands extension
            "-b", str(350000000), # block size for reading chromosome
            "-s", FASTA_file_ext, # FASTA file extension
            "-t", islands_gff, # island location
            #"-u", reads_files_dir, # reads file or directory
            "-c", chromosomes_file_dir, # chromosomes file or directory
            "-y", str(1), # nothing important
            "-f", str(flank_case), #if is 1, only output flank string that is not case 0
            "-A", str(num_anchor), #number of anchors
            #"-R", str(rank),   #only output rank >= rank
            "-bwtout", bwtout_25, #bwt segment output
            "-G", str(num_seg), #number of segments
            "-L", str(seg_len), #segment length
            #"-H", fix_hole_file, #fix hole file
            "-E", str(extend_bits), #extend bits when fix hole and fusion
            #"-M", str(total_mismatch), #total mismatch on splice reads
            #"-FM", str(total_fusion_mismatch), #total fusion mismatch
            #"-P", str(append_mismatch), #append mismatch
            "-threads", str(threads), #number of threads used
            "-tmp", params.temp_dir, #tmp dir
            "-fusion", params.fusion_dir,  #fusion dir
            "-fusionjunc", fusion_junction, #fusion junction
            #"-FQ", fqreads #fastq reads
            "-fusionsingleanchor", fusion_single_anchor #fusion junction
            ]
    else:
        cmd = [os.path.join(params.bin_dir,"mapsplice"),
        "-v", cur_ouput_dir,          # Output dir
        "-n", str(min_anchor_len), # Anchor length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-x", str(max_intron_length), # Maxmimum intron length
        "-i", str(min_intron_length), # Minimum intron length
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-p", str(islands_extension), # islands extension
        "-b", str(350000000), # block size for reading chromosome
        "-s", FASTA_file_ext, # FASTA file extension
        "-t", islands_gff, # island location
        "-u", reads_files_dir, # reads file or directory
        "-c", chromosomes_file_dir, # chromosomes file or directory
        "-y", str(1), # nothing important
        "-f", str(flank_case), #if is 1, only output flank string that is not case 0
        "-A", str(num_anchor), #number of anchors
        "-R", str(rank)   #only output rank >= rank
        ]
    logging.debug("separating unique and multiple mapped reads using %s" % ' '.join(splice_cmd))    
    runExt(cmd=cmd,errString='Spliced read alignment failed')
    return juncfile

def extract_maxlen(log_file):
    fh = open(log_file,"r")
    igot = fh.readlines()
    for line in igot:
        ls = line.split(' ')	    
        if ls[0].lower() == 'maxlen':
            return int(ls[1])
    logging.critical("Error: No max read length found in %s" % log_file)
    logging.shutdown()
    sys.exit(1)

def separatedmultipleunique(mps_unique_mapreads, mps_multiple_mapreads, cur_output_dir):
    logging.info("separating unique and multiple mapped reads")
    cmd = [os.path.join(bin_dir,"separatemapreads"), 
    cur_output_dir,
    "fixed_fixhole_divided_reads.txt",
    "fixed_hole_divided_reads.txt",
    "mapreads_divided_reads.txt",
    "fix_head_tail_divided_reads.txt",
    mps_unique_mapreads,
    mps_multiple_mapreads,
    "1"]
    if os.path.exists(os.path.join(cur_output_dir,mps_unique_mapreads)) and os.path.exists(os.path.join(cur_output_dir,mps_multiple_mapreads)) and params.rerun_all == 0:
        return mps_unique_mapreads
    runExt(cmd=cmd,errString='separated mapped reads failed')
    return (mps_unique_mapreads, mps_multiple_mapreads)

def merge_sort_sam(merged_sorted_by_tagname, merged_sorted_by_chromooffset, bwtmapped_sam, bwt_25bp_mapped, stat_file):
    logging.info("merge sorting mapped reads")
    bwt_25bp_mapped_mishandt_matched = "%s.mistailandhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_mishort_matched = "%s.mistailorhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_allmapped = "%s.allmapped" % params.bwt_25bp_mapped
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    cmd = [os.path.join(params.bin_dir,"merge_sort_sam"), 
        os.path.join(params.temp_dir + "splicedreads_remdupdivided_reads.txt"),
        os.path.join(params.temp_dir + "fixed_fixhole_exceed_divided_reads.txt"),
        os.path.join(params.temp_dir + "fixed_fixhole_exceed_f0_divided_reads.txt"),
        os.path.join(params.temp_dir + "fixed_fixhole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir + "fixed_hole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir + "fix_head_tail_noncanon_divided_reads.txt"),
        os.path.join(params.temp_dir + "mapreads_noncanon_divided_reads.txt"),
        bwtmapped_sam,
        bwt_25bp_mapped_mishandt_matched,
        bwt_25bp_mapped_mishort_matched,
        bwt_25bp_mapped_allmapped,			
        merged_sorted_by_tagname,
        merged_sorted_by_chromooffset,
        stat_file]
    runExt(cmd=cmd,errString='merge sort mapped reads failed')
    return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)

def merge_sort_sam_unspliced(merged_sorted_by_tagname, merged_sorted_by_chromooffset, bwtmapped_sam, bwt_25bp_mapped, stat_file):
    logging.info("merge sort mapped reads unspliced")
    bwt_25bp_mapped_mishandt_matched = "%s.mistailandhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_mishort_matched = "%s.mistailorhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_allmapped = "%s.allmapped" % params.bwt_25bp_mapped
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:   
        temp_fs = open(merged_sorted_by_tagname, "w")
        temp_fs.close()        
        temp_fs = open(bwtmapped_sam, "w")
        temp_fs.close()	
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    cmd = [os.path.join(params.bin_dir,"merge_sort_sam"), 
        bwtmapped_sam,
        bwt_25bp_mapped_mishandt_matched,
        bwt_25bp_mapped_mishort_matched,
        bwt_25bp_mapped_allmapped,			
        merged_sorted_by_tagname,
        merged_sorted_by_chromooffset,
        stat_file]       
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:        
        temp_fs = open(merged_sorted_by_tagname, "w")
        temp_fs.close()
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    runExt(cmd=cmd,errString='merge sort mapped reads failed')
    temp_fs = open(merged_sorted_by_tagname, "w")
    temp_fs.close()    
    temp_fs = open(bwtmapped_sam, "w")
    temp_fs.close()    
    return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)

def merge_sort_sam_canon(merged_sorted_by_tagname, merged_sorted_by_chromooffset, stat_file):
    logging.info("merge sort mapped reads canonical starting")    
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:
        temp_fs = open(merged_sorted_by_tagname, "w")
        temp_fs.close()        
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    cmd = [os.path.join(params.bin_dir,"merge_sort_sam"), 
    os.path.join(params.temp_dir,"splicedreads_remdupdivided_reads.txt"),
    os.path.join(params.temp_dir,"fixed_fixhole_exceed_divided_reads.txt"),		
    merged_sorted_by_tagname,
    merged_sorted_by_chromooffset,
    stat_file]
    runExt(cmd=cmd,errString='merge sort mapped reads failed')
    temp_fs = open(merged_sorted_by_tagname, "w")
    temp_fs.close()
    return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)

def merge_sort_sam_noncanon(merged_sorted_by_tagname, merged_sorted_by_chromooffset, stat_file):
    logging.info("merge sort mapped reads canonical starting")      
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:        
        temp_fs = open(merged_sorted_by_tagname, "w")
        temp_fs.close()	
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    cmd = [os.path.join(params.bin_dir,"merge_sort_sam"), 
        os.path.join(params.temp_dir,"fixed_fixhole_exceed_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_fixhole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_hole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fix_head_tail_noncanon_divided_reads.txt"),
        os.path.join(params.temp_dir,"mapreads_noncanon_divided_reads.txt"),			
        merged_sorted_by_tagname,
        merged_sorted_by_chromooffset,
        stat_file]
    runExt(cmd=cmd,errString='merge sort mapped reads canonical failed')
    temp_fs = open(merged_sorted_by_tagname, "w")
    temp_fs.close()
    return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)

def pairendmappedreads_sep(bwtmapped_sam, bwt_25bp_mapped, fusion_sam, pairend, single, cur_output_dir, maxhits):
    logging.info("pairendmappedreads_sep reads starting")
    if os.path.exists(output_dir_paired) and os.path.exists(output_dir_single) and params.rerun_all == 0:
        return (output_dir_paired, output_dir_single)
    bwt_25bp_mapped_mishandt_matched = "%s.mistailandhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_mishort_matched = "%s.mistailorhead.matched" % params.bwt_25bp_mapped
    bwt_25bp_mapped_allmapped = "%s.allmapped" % params.bwt_25bp_mapped
    cmd = [os.path.join(params.bin_dir,"pairend"), 
        os.path.join(params.temp_dir,"splicedreads_remdupdivided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_fixhole_exceed_divided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_fixhole_exceed_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_fixhole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fixed_hole_f0_divided_reads.txt"),
        os.path.join(params.temp_dir,"fix_head_tail_noncanon_divided_reads.txt"),
        os.path.join(params.temp_dir,"mapreads_noncanon_divided_reads.txt"),
        bwtmapped_sam,
        bwt_25bp_mapped_mishandt_matched,
        bwt_25bp_mapped_mishort_matched,
        bwt_25bp_mapped_allmapped,
        fusion_sam,			
        params.output_dir_paired,
        str(maxhits),
        params.output_dir_single]  
    runExt(cmd=cmd,errString='Pairedend failed')
    return (output_dir_paired, output_dir_single)

def compare2syntheticsam(mps_all_sam, synthe_sam, compared_out, comprange, all_junc, compared_offset_out,
    filter_sam, maxhits, uniquemapped, stat_file, anchor_width):
    logging.info("compare to synthetic sam starting")
    if os.path.exists(filter_sam) and os.path.exists(uniquemapped) and os.path.exists(stat_file) and params.rerun_all == 0:
        return (filter_sam, uniquemapped)
    entrpy_weight = 0.097718
    pqlen_weight = 0.66478
    ave_mis_weight = -0.21077
    cmd = [os.path.join(params.bin_dir,"compare2synthesam"), 
        mps_all_sam,
        synthe_sam,
        compared_out,
        str(comprange),
        all_junc,
        filter_sam,
        str(maxhits),
        uniquemapped,
        compared_offset_out,
        stat_file,
        str(anchor_width),
        str(entrpy_weight),
        str(pqlen_weight),
        str(ave_mis_weight)]
    runExt(cmd=cmd,errString='compare to synthetic sam failed')
    return (filter_sam, uniquemapped)

def compare2sam(mps_all_sam, comp_sam, compared_out, comprange, all_junc, compared_offset_out,
    filter_sam, maxhits, uniquemapped, stat_file, anchor_width):
    logging.info("compare to another sam starting")
    if os.path.exists(filter_sam) and os.path.exists(uniquemapped) and params.rerun_all == 0:
        return (filter_sam, uniquemapped)    
    cmd = [os.path.join(params.bin_dir,"Compare2Sam"), 
        mps_all_sam,
        comp_sam,
        compared_out,
        str(comprange),
        all_junc,
        filter_sam,
        str(maxhits),
        uniquemapped,
        compared_offset_out,
        stat_file,
        str(anchor_width)]
    runExt(cmd=cmd,errString='Compare to another sam failed')
    return (filter_sam, uniquemapped)

def sep_spliced_unspliced(merged_sam, unspliced_sam, spliced_sam):
    logging.info("separate sam by spliced unspliced on %s" % (merged_sam))    
    if os.path.exists(unspliced_sam) and os.path.exists(spliced_sam) and params.rerun_all == 0:
        temp_fs = open(unspliced_sam, "w")
        temp_fs.close
        temp_fs = open(merged_sam, "w")
        temp_fs.close()
        return (unspliced_sam, spliced_sam)
    cmd = [os.path.join(params.bin_dir,"separate_spliced_unspliced"), 
        merged_sam,
        unspliced_sam,
        spliced_sam]       
    runExt(cmd=cmd,errString='Separate spliced/unspliced reads failed')
    temp_fs = open(unspliced_sam, "w")
    temp_fs.close()
    temp_fs = open(merged_sam, "w")
    temp_fs.close()
    return (unspliced_sam, spliced_sam)

def filtersambyanchor(spliced_sam, anchor_width):
    logging.info("filter sam by anchor on %s starting" % (spliced_sam))    
    cmd = [os.path.join(params.bin_dir,"filterbyanchor"), 
        spliced_sam,
        str(anchor_width)]
    runExt(cmd=cmd,errString='filter sam by anchor failed')
    temp_fs = open("%s.longanchor" % spliced_sam, "w")
    temp_fs.close()
    return ("%s.longanchor" % spliced_sam, "%s.shortanchor" % spliced_sam)

def filterbyintronlenhmer(spliced_sam, intron_len, seglen):
    logging.info("filter by intronlen hmer on %s starting" % (spliced_sam))
    cmd = [os.path.join(params.bin_dir,"filterbyintronlenhmer"), 
        spliced_sam,
        str(intron_len),
        str(seglen)]
    runExt(cmd=cmd,errString='filter by intron length hmmer failed')
    temp_fs = open("%s.inintronlenhmer" % spliced_sam, "w")
    temp_fs.close()
    return ("%s.inintronlenhmer" % spliced_sam,"%s.notinintronlenhmer" % spliced_sam)

def filterbysmallexon(spliced_sam, seglen):
    logging.info("filter by small exon on %s" % (spliced_sam))
    cmd = [os.path.join(params.bin_dir,"filterbysmallexon"), 
        spliced_sam,
        str(seglen)]
    runExt(cmd=cmd,errString='filter by small exon failed')
    temp_fs = open("%s.insmallexon" % spliced_sam, "w")
    temp_fs.close()
    return ("%s.insmallexon" % spliced_sam, "%s.notinsmallexon" % spliced_sam)

def filternotinunmapped(spliced_sam, unmapped_reads, fa_fq):
    logging.info("filter spliced sam not in unmapped reads on %s starting" % (unmapped_reads))
    cmd = [os.path.join(params.bin_dir,"filternotinunmapped"), 
        spliced_sam,
        unmapped_reads,
        str(fa_fq)]
    runExt(cmd=cmd,errString='filter sam by anchor failed')
    temp_fs = open("%s.inunmapped" % spliced_sam, "w")
    temp_fs.close()
    return ("%s.notinunmapped" % spliced_sam, "%s.inunmapped" % spliced_sam)

def filterbyrepeated_reads(spliced_sam, repeated_reads, fa_fq):
    logging.info("filter by repeated reads on %s starting" % (repeated_reads))    
    cmd = [os.path.join(params.bin_dir,"filterbyrepeated_reads"), 
        spliced_sam,
        repeated_reads,
        str(fa_fq)]
    runExt(cmd=cmd,errString='filter by repeated reads failed')
    temp_fs = open(spliced_sam + ".notinrepeat", "w")
    temp_fs.close()
    return (spliced_sam + ".inrepeat", spliced_sam + ".notinrepeat")

def filterbyunsplicedmapped(spliced_sam, unspliced_mapped_sam):
    logging.info("filter by unsplicedmapped on %s starting" % (unspliced_mapped_sam))    
    cmd = [os.path.join(params.bin_dir,"filterbyunsplicedmapped"), 
        spliced_sam,
        unspliced_mapped_sam]
    runExt(cmd=cmd,errString='filter by unspliced mapped reads failed')
    temp_fs = open(spliced_sam + ".notinunsplicedmapped", "w")
    temp_fs.close()    
    return (spliced_sam + ".notinunsplicedmapped", spliced_sam + ".inunsplicedmapped")

def filtersambyisland(spliced_sam, island_file):
    logging.info("filter sam by islandon %s starting" % (island_file))    
    cmd = [os.path.join(params.bin_dir,"filterbyisland"), 
    spliced_sam,
    island_file]
    runExt(cmd=cmd,errString='filter by islands failed')
    temp_fs = open(spliced_sam + ".inisland", "w")
    temp_fs.close()
    return (spliced_sam + ".inisland", spliced_sam + ".notinisland")

def FilterMultipleMapped(mps_all_sam, all_junc, filter_sam, maxhits, uniquemapped, stat_file, log_file):
    logging.info("Filter Multiple Mapped starting")
    entrpy_weight = 0.097718
    pqlen_weight = 0.66478
    ave_mis_weight = -0.21077
    if os.path.exists(filter_sam) and os.path.exists(uniquemapped) and params.rerun_all == 0:
        return (filter_sam, uniquemapped)
    cmd = [os.path.join(params.bin_dir,"FilterMultipleMappedByRead"), 
    mps_all_sam,
    all_junc,
    filter_sam,
    str(maxhits),
    uniquemapped,
    stat_file,
    str(entrpy_weight),
    str(pqlen_weight),
    str(ave_mis_weight)]
    runExt(cmd=cmd,errString='filter by multiple mapped reads failed',logFile=log_file)
    return (filter_sam, uniquemapped)

def merge_sort_sam2(merged_sorted_by_tagname, merged_sorted_by_chromooffset, mapped1, mapped2, stat_file):
    logging.info("merge sort sam2 starting")
    if os.path.exists(merged_sorted_by_tagname) and os.path.exists(merged_sorted_by_chromooffset) and params.rerun_all == 0:
        temp_fs = open(merged_sorted_by_tagname, "w")
        temp_fs.close()   
        return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)
    cmd = [os.path.join(params.bin_dir,"merge_sort_sam"), 
    mapped1,
    mapped2,
    merged_sorted_by_tagname,
    merged_sorted_by_chromooffset,
    stat_file]       
    runExt(cmd=cmd,errString='Merge sam sort failed')
    temp_fs = open(merged_sorted_by_tagname, "w")
    temp_fs.close()    
    return (merged_sorted_by_tagname, merged_sorted_by_chromooffset)

def pairsam(allsam, pairend, single, cur_output_dir, maxhits, log_file):
    logging.info("pairend mapped reads starting")    
    if os.path.exists(output_dir_paired) and os.path.exists(output_dir_single) and params.rerun_all == 0:
        return (output_dir_paired, output_dir_single)
    output_dir_paired = os.path.join(cur_output_dir,pairend)
    output_dir_single = os.path.join(cur_output_dir,single)    
    cmd = [os.path.join(params.bin_dir,"pairend"), 
    allsam,
    str(maxhits),
    output_dir_paired,
    output_dir_single]    
    runExt(cmd=cmd,errString='paired end failed')
    return (output_dir_paired, output_dir_single)

def parseCluster(merge_pair_sam, output_dir, log_file):
    logging.info("parse cluster regions")  
    cmd = [os.path.join(params.bin_dir,"parseCluster"), 
    merge_pair_sam,
    output_dir]
    runExt(cmd=cmd,errString='Paired end failed',logFile=log_file)

def cluster(cluster_dir, log_file):
    logging.info("cluster regions starting")
    cmd = [os.path.join(params.bin_dir,"cluster"),cluster_dir]    
    runExt(cmd=cmd,errString='Cluster regions failed') 

def ReadRegions(region_file, single_sam, reads_file, out_path, format_flag, chrom_dir, output_dir_file, extend_len, log_file):
    logging.info("read regions starting")    
    if os.path.exists(output_dir_file) and params.rerun_all == 0:
        return output_dir_file
    format_int = 0    
    if format_flag == "-q":
        format_int = 1
    cmd = [os.path.join(params.bin_dir,"ReadRegions",logFile=log_file), 
    region_file,
    single_sam,
    reads_file,
    out_path,
    str(format_int),
    chrom_dir,
    output_dir_file,
    str(extend_len)]
    runExt(cmd=cmd,errString='Resort mapped reads failed') 
    return output_dir_file

def FilterFusionCandidatesByClusterRegions(region_file, single_sam, fusion_candidate_file, extend_len, seg_num, log_file):
    logging.info("filter fusion candidate by regions")
    if os.path.exists(fusion_candidate_file + ".remained.formated") and params.rerun_all == 0:
        return fusion_candidate_file + ".remained.formated"

    cmd = [os.path.join(params.bin_dir,"FilterFusionCandidatesByClusterRegions"), 
    region_file,
    single_sam,
    fusion_candidate_file,
    str(extend_len),
    str(seg_num)]
    runExt(cmd=cmd,errString='Resort mapped reads failed')
    return fusion_candidate_file + ".remained.formated"

def pairing_fusion_normal_aligned(region_file, single_sam, fusion_candidate_file, extend_len, log_file):
    logging.info("pairing fusion normal aligned")
    if os.path.exists(fusion_candidate_file + ".paired") and \
       os.path.exists(fusion_candidate_file + ".fusion_single") and \
       os.path.exists(fusion_candidate_file + ".normal_single") and \
       params.rerun_all == 0:
        return fusion_candidate_file + ".paired"
    cmd = [os.path.join(params.bin_dir,"pairing_fusion_normal_aligned"), 
    region_file,
    single_sam,
    fusion_candidate_file,
    str(extend_len)]
    runExt(cmd=cmd,errString='Pairing fusion normal aligned failed',logFile=log_file)
    return fusion_candidate_file + ".paired"

def load_fusion_single_anchor_chrom_seq(fusion_candidate_file, fusion_candidate_file_loaded, chrom_dir, log_file):
    logging.info("load_fusion_single_anchor_chrom_seq")    
    if os.path.exists(fusion_candidate_file_loaded) and params.rerun_all == 0:
        return fusion_candidate_file_loaded
    cmd = [os.path.join(params.bin_dir,"load_fusion_single_anchor_chrom_seq"), 
    fusion_candidate_file,
    fusion_candidate_file_loaded,
    chrom_dir]
    runExt(cmd=cmd,errString='Load fusion single anchor chromosome sequence failed',logFile=log_file)
    return fusion_candidate_file_loaded

def generate_bash_file_and_run(director_file, bash_file, abs_path, arguments, bin_dir, log_file):
    logging.info("generate bash file and run")
    quote_bin_dir = '"%s"' % params.bin_dir
    cmd = [os.path.join(params.bin_dir,"generate_bash_file_and_run"), 
    director_file,
    bash_file,
    abs_path,
    arguments,
    quote_bin_dir]
    runExt(cmd=cmd,errString='Generate bash file and run failed')
    cmd = ["chmod","700",bash_file]
    runExt(cmd=cmd,errString='Make bash file executable')
    runExt(cmd=['bash',bash_file],errString='Execute bash file',logFile=log_file)
    return bash_file

def convert_to_abs_offset(director_file, sam_output_file, fusion_output_file, abs_path, log_file):
    logging.info("convert to abs offset")    
    if os.path.exists(sam_output_file) and os.path.exists(fusion_output_file) and params.rerun_all == 0:
        return (sam_output_file, fusion_output_file)
    cmd = [os.path.join(params.bin_dir,"convert_to_abs_offset"), 
    director_file,
    sam_output_file,
    fusion_output_file,
    abs_path]
    runExt(cmd=cmd,errString='Convert to absolute offset',logFile=log_file)
    return (sam_output_file, fusion_output_file)

def parsePER(PERsam, log_file):
    logging.info("parse PER sam file")
    test_file = fusion_data_PER_dir + "chrXchrX.txt"    
    if os.path.exists(test_file) and params.rerun_all == 0:
        return
    cmd = [os.path.join(params.bin_dir,"parsePER"), 
    PERsam,
    fusion_dir]
    runExt(cmd=cmd,errString='parse PER sam file')
    
def parseSingle(PERsam, log_file):
    logging.info("parse Single sam file")
    test_file = fusion_data_single_dir + "chrX.txt"    
    if os.path.exists(test_file) and params.rerun_all == 0:
        return
    cmd = [os.path.join(params.bin_dir,"parseSingle"), 
    PERsam,
    fusion_dir]
    runExt(cmd=cmd,errString='parse single sam file',logFile=log_file)

def PERall(log_file):
    logging.info("Map PER reads")
    test_file = params.fusion_result_PER_prob_dir + "PERprob_chrXchrX.sam"    
    if os.path.exists(test_file) and params.rerun_all == 0:
        return
    cmd = [os.path.join(params.bin_dir,"MapPERall"),"all",params.bin_dir,params.fusion_dir]
    runExt(cmd=cmd,errString='Map PER all',logFile=log_file)

def runPER(PERsam, Singlesam):
    logging.info("processing PER reads")
    parsePER(PERsam, params.logging_dir + "PERsam.log")    
    parseSingle(Singlesam, params.logging_dir + "Singlesam.log")
    PERall(params.logging_dir + "PERall.log")

def pairendmappedreads(allsam, fusion_sam, pairend, single, cur_output_dir, maxhits):
    logging.info("pairend mapped reads")    
    output_dir_paired = os.path.join(cur_output_dir,pairend)
    output_dir_single = os.path.join(cur_output_dir,single)
    if os.path.exists(output_dir_paired) and os.path.exists(output_dir_single) and params.rerun_all == 0:
        return (output_dir_paired, output_dir_single)
    cmd = [bin_dir + "pairend", 
    allsam,
    fusion_sam,
    output_dir_paired,
    str(maxhits),
    output_dir_single]    
    runExt(cmd=cmd,errString='Paired ends mapped reads all')
    return (output_dir_paired, output_dir_single)

def pairendmappedreads3(sam1, sam2, sam3, pairend, single, cur_output_dir, maxhits):
    logging.info("pairend mapped reads 3")    
    output_dir_paired = os.path.join(cur_output_dir,pairend)
    output_dir_single = os.path.join(cur_output_dir,single)    
    if os.path.exists(output_dir_paired) and os.path.exists(output_dir_single) and params.rerun_all == 0:
        return (output_dir_paired, output_dir_single)
    cmd = [os.path.join(params.bin_dir,"pairend"), 
    sam1,
    sam2,
    sam3,
    output_dir_paired,
    str(maxhits),
    output_dir_single]    
    runExt(cmd=cmd,errString='Paired end mapped reads 3')
    return (output_dir_paired, output_dir_single)

def separatedmultipleunique_non_canon(mps_unique_mapreads, mps_multiple_mapreads, cur_output_dir):
    logging.info("separate unique and multiple mapped reads non canonical")
    cmd = [os.path.join(params.bin_dir,"separatemapreads"), 
    cur_output_dir,
    "fixed_fixhole_f0_divided_reads.txt",
    "fixed_hole_f0_divided_reads.txt",
    "mapreads_noncanon_divided_reads.txt",
    "fix_head_tail_noncanon_divided_reads.txt",
    mps_unique_mapreads,
    mps_multiple_mapreads,
    "1"]
    runExt(cmd=cmd,errString='Separate multiple mapped and unique reads')
    return (mps_unique_mapreads, mps_multiple_mapreads)

def separatedmultipleunique1(combinefile, unique_mapreads, multiple_mapreads, cur_output_dir):
    logging.info("separate combined to unique and multiple mapped reads")
    if os.path.exists(cur_output_dir + unique_mapreads) and os.path.exists(os.path.join(cur_output_dir,multiple_mapreads)) and params.rerun_all == 0:
        return unique_mapreads
    cmd = [os.path.join(params.bin_dir,"separatemapreads"), 
    cur_output_dir,
    combinefile,
    unique_mapreads,
    multiple_mapreads,
    "1"]       
    runExt(cmd=cmd,errString='Separate multiple and unique mapped reads')
    return (unique_mapreads, multiple_mapreads)

def separatedmultipleuniquefusion(combinefile, unique_mapreads, multiple_mapreads, stat_file):
    logging.info("separate combined fusion to unique and multiple mapped reads")
    if os.path.exists(unique_mapreads) and os.path.exists(multiple_mapreads) and params.rerun_all == 0:
        return unique_mapreads
    cmd = [os.path.join(params.bin_dir,"separateuniquefusion"), 
    combinefile,
    unique_mapreads,
    multiple_mapreads,
    stat_file]
    runExt(cmd=cmd,errString='Separate multiple and unique fusion')
    return (unique_mapreads, multiple_mapreads)

def separateuniquefusion_newfmt(combinefile, unique_mapreads, multiple_mapreads, stat_file):
    logging.info("separate combined new fmt fusion to unique and multiple mapped reads")
    if os.path.exists(unique_mapreads) and os.path.exists(multiple_mapreads) and params.rerun_all == 0:
        return unique_mapreads
    cmd = [os.path.join(params.bin_dir,"separateuniquefusion_newfmt"), 
    combinefile,
    unique_mapreads,
    multiple_mapreads,
    stat_file]
    runExt(cmd=cmd,errString='separate combined new fmt fusion to unique and multiple mapped reads')
    return (unique_mapreads, multiple_mapreads)

def separate_canon_noncanon(combinejunc, canon_junc, noncanon_junc):
    desc = "separate combined junction to canon and noncanon"
    logging.info(desc)
    if os.path.exists(canon_junc) and os.path.exists(noncanon_junc) and params.rerun_all == 0:
        return (canon_junc, noncanon_junc)
    cmd = [os.path.join(params.bin_dir,"separate_canon_noncanon"), 
    combinejunc,
    canon_junc,
    noncanon_junc]      
    runExt(cmd=cmd,errString=desc)
    return (canon_junc, noncanon_junc)

def count_canon_noncanon(combinejunc, canon, noncanon, log_file):
    desc = "count combined junction to canon and noncanon"    
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"count_canon_noncanon"), combinejunc, canon, noncanon]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (canon, noncanon)
	
def filterjuncbyminmis(combinejunc, min_mismatch, in_min_mis, not_in_min_mis):
    desc="filter junction by min mismatch" 
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"filterbyjuncminmis"),combinejunc, str(min_mismatch), in_min_mis, not_in_min_mis]
    runExt(cmd=cmd,errString=desc)
    return (in_min_mis, not_in_min_mis)

def filterjuncbysmalldeletion(combinejunc, min_intron, in_small_deletion, not_in_small_deletion, log_file):
    desc="filter junction by small deletion"
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"filterjuncbysmalldeletion"), 
        combinejunc, str(min_intron), in_small_deletion, not_in_small_deletion]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (in_small_deletion, not_in_small_deletion)

def filterfusionjuncbyminmis(combinejunc, min_mis, in_min_mis, not_in_min_mis, log_file):
    desc = "filter fusion junction by min mismatch"
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"filterfusionjuncbyminmis"), 
        combinejunc, str(min_mis), in_min_mis, not_in_min_mis]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (in_min_mis, not_in_min_mis)

def filtermappedreads(samfile, notfiltered, filtered, objreads, opt):
    desc = "filter mapped reads"
    logging.info(desc)
    if os.path.exists(filtered) and os.path.exists(notfiltered) and params.rerun_all == 0:
        return (filtered, notfiltered)
    cmd = [os.path.join(params.bin_dir,"filtermappedreads"),
    opt,
    objreads,
    notfiltered,
    filtered,
    samfile]
    runExt(cmd=cmd,errString=desc)
    return (filtered, notfiltered)

def separatedfullymapped(bwt_mapped_sam, bwt_25bp_mapped, cur_output_dir):
    desc = "separate fully mapped unique and multiple mapped reads"
    logging.info(desc)
    if os.path.exists(os.path.join(cur_output_dir,"fully_unique.txt")) and \
        os.path.exists(os.path.join(cur_output_dir,"fully_multiple.txt")) and \
        params.rerun_all == 0:
            return "fully_unique.txt"
    bwt_25bp_mapped_mishandt_matched = bwt_25bp_mapped + ".mistailandhead.matched"    
    bwt_25bp_mapped_mishort_matched = bwt_25bp_mapped + ".mistailorhead.matched"
    bwt_25bp_mapped_allmapped = bwt_25bp_mapped + ".allmapped"    
    separatemapreads_cmd = [os.path.join(params.bin_dir,"separatemapreads"), 
    cur_output_dir,
    bwt_mapped_sam,
    bwt_25bp_mapped_mishandt_matched,
    bwt_25bp_mapped_mishort_matched,
    bwt_25bp_mapped_allmapped,
    "fully_unique.txt",
    "fully_multiple.txt",
    "0"]    
    runExt(cmd=cmd,errString=desc)
    return ("fully_unique.txt", "fully_multiple.txt")

def countline(countfile, log_file):
    desc = "count line"
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"countline"),countfile]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    
def write_current_stats(cur_stats):
    mapsplice_log = open(params.logging_dir + "current_stats.log", "w")
    mapsplice_log.write(cur_stats)
    mapsplice_log.close()

    
def filtermultiplemapped(mps_multiple_mapreads, mps_filtered_multiple, junctions, maxhits, cur_output_dir):
    desc = "filter multiple mapped reads"
    logging.info(desc)
    if os.path.exists(os.path.join(output_dir,mps_filtered_multiple)) and params.rerun_all == 0:
        return mps_filtered_multiple    
    cmd = [os.path.join(params.bin_dir,"filtermapreads"), 
    cur_output_dir,
    mps_multiple_mapreads,
    str(maxhits),
    junctions,
    mps_filtered_multiple]    
    runExt(cmd=cmd,errString=desc)
    return mps_filtered_multiple

def sam2junc_all(converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, min_anchor_length):
    desc = "convert sam file to junctions"    
    if os.path.exists(converted_junc) and params.rerun_all == 0:
        return converted_junc
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"newsam2junc"), 
    converted_junc,
    str(read_width),
    chromosomes_file_dir,
    str(min_intron_length),str(max_intron_length),
    str(min_anchor_length),
    temp_dir + "splicedreads_remdupdivided_reads.txt",
    temp_dir + "fixed_fixhole_exceed_divided_reads.txt",
    temp_dir + "fixed_fixhole_exceed_f0_divided_reads.txt",
    temp_dir + "fixed_fixhole_f0_divided_reads.txt",
    temp_dir + "fixed_hole_f0_divided_reads.txt",
    temp_dir + "fix_head_tail_noncanon_divided_reads.txt",
    temp_dir + "mapreads_noncanon_divided_reads.txt"]    
    runExt(cmd=cmd,errString=desc)
    return converted_junc

def sam2junc4(mapped1, mapped2, mapped3, mapped4, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, min_anchor_length):
    desc = "convert sam file to junctions"     
    if os.path.exists(converted_junc) and params.rerun_all == 0:
        return converted_junc
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"newsam2junc"), 
    converted_junc,
    str(read_width),
    chromosomes_file_dir,
    str(min_intron_length),str(max_intron_length),
    str(min_anchor_length),
    mapped1, 
    mapped2,
    mapped3,
    mapped4]    
    runExt(cmd=cmd,errString=desc)
    return converted_junc

def sam2junc(mps_unique_mapped, mps_multiple_mapped, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, cur_output_dir, min_anchor_length):
    desc = "convert sam file to junctions"
    logging.info(desc)
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_mps_multiple_mapped = os.path.join(cur_output_dir,mps_multiple_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    cmd = [os.path.join(params.bin_dir,"newsam2junc"), 
    output_dir_converted_junc,
    str(read_width),
    chromosomes_file_dir,
    str(min_intron_length),str(max_intron_length),
    str(min_anchor_length),
    output_dir_mps_unique_mapped, 
    output_dir_mps_multiple_mapped]    
    runExt(cmd=cmd,errString=desc)
    return output_dir_converted_junc

def sam2junc1(mps_unique_mapped, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, cur_output_dir, min_anchor_length, log_file):
    desc = "convert sam file to junctions"
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:	
        if os.path.exists(output_dir_converted_junc + ".sepdir"):
            shutil.rmtree(output_dir_converted_junc + ".sepdir")
        return output_dir_converted_junc    
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"newsam2junc"), 
    output_dir_converted_junc,
    str(read_width),
    chromosomes_file_dir,
    str(min_intron_length),str(max_intron_length),
    str(min_anchor_length),
    output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    if os.path.exists(output_dir_converted_junc + ".sepdir"):
        shutil.rmtree(output_dir_converted_junc + ".sepdir")	    
    return output_dir_converted_junc

def junc2bed(junction_file, junction_bed, log_file):
    desc = "convert junction file to bed format"
    if os.path.exists(junction_bed) and params.rerun_all == 0:
        return junction_bed
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"junc2bed"),junction_file,junction_bed]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return junction_bed

def junc2bed2(junction_file1, junction_file2, junction_bed, log_file):
    desc = "convert junction file to bed format 2"
    if os.path.exists(junction_bed) and params.rerun_all == 0:
        return junction_bed
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"junc2bed"),junction_file1,junction_file2,junction_bed]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return junction_bed

def sam2juncarray(sam_file_array, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, cur_output_dir, min_anchor_length, log_file):
    desc = "convert sam files to junctions" 
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        if os.path.exists(output_dir_converted_junc + ".sepdir"):
            shutil.rmtree(output_dir_converted_junc + ".sepdir")
        return output_dir_converted_junc
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"newsam2junc"), 
        output_dir_converted_junc,
        str(read_width),
        chromosomes_file_dir,
        str(min_intron_length),str(max_intron_length),
        str(min_anchor_length)]    
    for sam_file in sam_file_array:
        cmd.append(sam_file)
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    if os.path.exists(output_dir_converted_junc + ".sepdir"):
        shutil.rmtree(output_dir_converted_junc + ".sepdir")
    return output_dir_converted_junc

def sam2juncarray_paired(sam_file_array, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, cur_output_dir, min_anchor_length, paired, log_file):
    desc = "convert array paired sam file to junctions"
    logging.info(desc)
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    cmd = [os.path.join(params.bin_dir,"newsam2junc_paired"), 
        output_dir_converted_junc,
        str(read_width),
        chromosomes_file_dir,
        str(min_intron_length),str(max_intron_length),
        str(min_anchor_length),
        paired]    
    for sam_file in sam_file_array:
        cmd.append(sam_file)
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    if os.path.exists(output_dir_converted_junc + ".sepdir"):
        shutil.rmtree(output_dir_converted_junc + ".sepdir")
    return output_dir_converted_junc

def bed2bigbed(junction_bed, junction_bigbed, all_chromosomes_file):
    desc = "convert junction bed to big bed format"
    if os.path.exists(junction_bigbed) and params.rerun_all == 0:
        return junction_bigbed    
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"remove_firstline"), 
        junction_bed,
        junction_bed + ".rm_1st_line"]    
    runExt(cmd=cmd,errString=desc)
    #bedToBigBed input.bed chrom.sizes myBigBed.bb
    cmd = [os.path.join(params.bin_dir,"bedToBigBed"), 
    junction_bed + ".rm_1st_line",
    all_chromosomes_file + ".chrom.sizes",
    junction_bigbed]    
    runExt(cmd=cmd,errString=desc)
    temp_fs = open(junction_bed + ".rm_1st_line", "w")
    temp_fs.close()
    return junction_bigbed

def wig2bigwig(coverage_wig, coverage_big_wig, all_chromosomes_file):
    desc = "convert coverage wig to big wig format" 
    if os.path.exists(coverage_big_wig) and params.rerun_all == 0:
        return coverage_big_wig    
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"remove_firstline"), 
        coverage_wig,
        coverage_wig + ".rm_1st_line"]    
    runExt(cmd=cmd,errString=desc) 	
    cmd = [os.path.join(params.bin_dir,"wigToBigWig"), 
        coverage_wig + ".rm_1st_line",
        all_chromosomes_file + ".chrom.sizes",
        coverage_big_wig]    
    runExt(cmd=cmd,errString=desc) 	
    temp_fs = open(coverage_wig + ".rm_1st_line", "w")
    temp_fs.close()    
    return coverage_big_wig

def filter_junc_by_min_mis_lpq(junction_file, remained_junc, filtered_out_junc, min_mismatch, min_lpq, log_file):
    desc = "filter junction by min mis and min lpq"
    if os.path.exists(filtered_out_junc) and os.path.exists(remained_junc) and params.rerun_all == 0:
        return (remained_junc, filtered_out_junc)
    logging.info(desc)    
    if min_lpq > 0.5:
        min_lpq = 0.5    
    cmd = [os.path.join(params.bin_dir,"filter_1hits"),
        junction_file,
        str(min_mismatch),
        str(min_lpq),
        remained_junc,
        filtered_out_junc]
    runExt(cmd=cmd,errString=desc,logFile=log_file) 	
    return (remained_junc, filtered_out_junc)

def filterjuncbyROCarguNoncanon(junction_file, remained_junc, filtered_out_junc, entropy_weight, lpq_weight, ave_mis_weight, min_score, log_file):
    desc = "filter junc by ROC argu noncanonical"
    if os.path.exists(filtered_out_junc) and os.path.exists(remained_junc) and params.rerun_all == 0:
        return (remained_junc, filtered_out_junc)
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"filterjuncbyROCarguNonCanonical"),
        junction_file,
        str(entropy_weight),
        str(lpq_weight),
        str(ave_mis_weight),
        '0',
        '0',
        str(min_score),
        '5',
        remained_junc,
        filtered_out_junc]    
    runExt(cmd=cmd,errString=desc,logFile=log_file) 	
    return (remained_junc, filtered_out_junc)

def filterjuncbyROCargu(junction_file, remained_junc, filtered_out_junc, entropy_weight, lpq_weight, ave_mis_weight, min_score, log_file):
    desc = "filter junc by ROC argu"
    if os.path.exists(filtered_out_junc) and os.path.exists(remained_junc) and params.rerun_all == 0:
        return (remained_junc, filtered_out_junc)
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"filterjuncbyROCargu"),
        junction_file,
        str(entropy_weight),
        str(lpq_weight),
        str(ave_mis_weight),
        str(min_score),
        remained_junc,
        filtered_out_junc]    
    runExt(cmd=cmd,errString=desc,logFile=log_file) 	
    return (remained_junc, filtered_out_junc)

def SamHandler_sam2junc1(mps_unique_mapped, converted_junc, chromosomes_file_dir, 
        read_width, min_intron_length, max_intron_length, cur_output_dir):
    desc = "SamHandler convert sam file to junctions"
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"SamHandlerSam2junc"), 
        output_dir_converted_junc,
        str(read_width),
        chromosomes_file_dir,
        str(min_intron_length),str(max_intron_length),
        output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc)
    return output_dir_converted_junc

def fusionsam2junc1(mps_unique_mapped, converted_junc, read_width, cur_output_dir, log_file):
    desc = "convert fusion sam file to junctions"
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)    
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"fusionsam2junc"), 
        output_dir_converted_junc,
        str(read_width),
        output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return output_dir_converted_junc

def fusionsam2juncplus1(mps_unique_mapped, converted_junc, read_width, cur_output_dir, log_file):
    desc = "convert fusion sam file to junctions plus1" % (right_now())
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)    
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"fusionsam2juncplus1"), 
        output_dir_converted_junc,
        str(read_width),
        output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return output_dir_converted_junc

def fusionsam2junc_filteranchor(mps_unique_mapped, converted_junc, read_width, cur_output_dir, min_anchor, log_file):
    desc = "convert fusion sam file to junctions and filter by anchor" 
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)      
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"fusionsam2junc_filteranchor"), 
        output_dir_converted_junc,
        str(read_width),
        str(min_anchor),
        output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return output_dir_converted_junc

def fusionsam2junc_filteranchor_newfmt(mps_unique_mapped, converted_junc, 
        read_width, cur_output_dir, min_anchor,chromosomes_file_dir, log_file):
    desc = "convert new fusion sam file to junctions and filter by anchor" 
    output_dir_mps_unique_mapped = os.path.join(cur_output_dir,mps_unique_mapped)    
    output_dir_converted_junc = os.path.join(cur_output_dir,converted_junc)
    if os.path.exists(output_dir_converted_junc) and params.rerun_all == 0:
        return output_dir_converted_junc
    logging.info(desc)     
    cmd = [os.path.join(params.bin_dir,"fusionsam2junc_filteranchor_newfmt"), 
        output_dir_converted_junc,
        str(read_width),
        str(min_anchor),
        chromosomes_file_dir,
        output_dir_mps_unique_mapped]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return output_dir_converted_junc

def extract_fusion_chr_seq(in_junc, converted_junc, chr_dir, extract_len, log_file):
    desc = "extract fusion chromosome sequence"  
    if os.path.exists(converted_junc) and params.rerun_all == 0:
        return converted_junc
    logging.info(desc)     
    cmd = [os.path.join(params.bin_dir,"extract_fusion_chr_seq"), 
        in_junc,
        converted_junc,
        chr_dir,
        str(extract_len)]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return converted_junc

def filter_fusion_by_repeat(fusion_junc, fusion_junc_out, fusion_junc_append_out, filtered_fusion, chrom_blat):    
    desc = "filter fusion by repeat" 
    if os.path.exists(filtered_fusion) and params.rerun_all == 0:
        return filtered_fusion # was annot_gene ??!!
    blatJunct_log = open(os.path.join(params.logging_dir,"blatJunct.log"), "w")
    filterBlat_log = open(os.path.join(params.logging_dir,"filterBlat.log"), "w")
    filtered_fusion_log = open(filtered_fusion, "w")
    blatJunct_cmd = ["python", os.path.join(params.bin_dir,"blatJunct.py"), fusion_junc, chrom_blat]
    filterBlat_cmd = ["python", os.path.join(params.bin_dir,"filterBlat.py"), fusion_junc, fusion_junc_out]
    printJunct_cmd = ["python", os.path.join(params.bin_dir,"printJunct.py"), fusion_junc_append_out]
    runExt(cmd=blatJunct_cmd,errString=desc,logFile=blatJunct_log)
    runExt(cmd=filterBlat_cmd,errString=desc,logFile=filterBlat_log)
    runExt(cmd=printJunct_cmd,errString=desc,logFile=filtered_fusion_log)
    return filtered_fusion

def annot_genef(fusion_junc, normal_junc, know_gene, annot_gene, log_file):
    """ renamed from annot_gene which will clash in the name space! """
    desc = "annotate gene from normal junction and fusion junction" 
    if os.path.exists(annot_gene) and params.rerun_all == 0:
        return annot_gene
    logging.info(desc)     
    cmd = [os.path.join(params.bin_dir,"search_fusion_gene_new"), 
        '-g', know_gene,
        '-f', fusion_junc,
        '-n', normal_junc,
        '-o', annot_gene,
        '-n_header']    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return annot_gene

def fusionsam2maf(out_maf_file, chrom_size_file, fusion_sam_file, log_file):
    desc = "convert fusion sam file to maf file"
    logging.info(desc)        
    if os.path.exists(out_maf_file) and params.rerun_all == 0:
        return out_maf_file
    cmd = [os.path.join(params.bin_dir,"fusionsam2maf"), 
        out_maf_file,
        chrom_size_file,
        fusion_sam_file]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return out_maf_file

def filterfusionjuncbystartend(normal_junc, fusion_junc, out_put_root, range, log_file):
    desc = "filter fusion sam file to by start end"     
    if os.path.exists(out_put_root + ".matched") and params.rerun_all == 0:
        return out_put_root + ".matched"
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"MatchStartEndFusion"), 
        normal_junc,
        fusion_junc,
        out_put_root,
        str(range)]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return out_put_root + ".matched"

def resortmappedreads(mps_unique_mapreads, mps_multiple_mapreads, bwtmapped_sam, bwt_25bp_mapped, resorted_offset, resorted_tagname, cur_output_dir):
    desc = "resort mapped reads by offset and tagname"
    bwt_25bp_mapped_mishandt_matched = bwt_25bp_mapped + ".mistailandhead.matched"    
    bwt_25bp_mapped_mishort_matched = bwt_25bp_mapped + ".mistailorhead.matched"
    bwt_25bp_mapped_allmapped = bwt_25bp_mapped + ".allmapped"    
    output_dir_resorted_offset = os.path.join(cur_output_dir,resorted_offset)
    output_dir_resorted_tagname = os.path.join(cur_output_dir,resorted_tagname)
    if os.path.exists(output_dir_resorted_offset) and os.path.exists(output_dir_resorted_tagname) and params.rerun_all == 0:
        return (output_dir_resorted_offset, output_dir_resorted_tagname)
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"resortmapreads"), 
        mps_unique_mapreads,
        mps_multiple_mapreads,
        bwt_25bp_mapped_mishandt_matched,
        bwt_25bp_mapped_mishort_matched,
        bwt_25bp_mapped_allmapped,
        bwtmapped_sam,
        output_dir_resorted_offset,
        output_dir_resorted_tagname]    
    runExt(cmd=cmd,errString=desc)
    return (output_dir_resorted_offset, output_dir_resorted_tagname)

def call_rmap(syn_junctions, 
              seed_length,
              read_width,
              unmapped_reads,
              splice_mismatches,
              anchor_width,
              rank):
    desc = "Aligning synthetic junction with rmap"     
    logging.info(desc)
    juncfile_rmapped = os.path.join(output_dir,"junctions_rmapped.txt")
    cmd = [os.path.join(params.bin_dir,"rmap"),
        "-L", str(read_width - anchor_width), # synthetic length
        "-m", str(splice_mismatches), # Mismatches allowed in extension
        "-h", str(seed_length), # Seed size for reads
        "-w", str(read_width), # read width for reads
        "-r", juncfile_rmapped, # output junction file
        "-u", unmapped_reads, # reads file or directory
        "-c", syn_junctions, # synthetic junctions
        "-R", str(rank), #rank for filter
        "whatever"]
    runExt(cmd=cmd,errString=desc)
    return juncfile_rmapped

def build_chromosome_index(user_splice_fasta, user_splices_out_prefix):
    desc = "Indexing chromosome sequences"
    logging.info(desc)
    bowtie_build_log = open(os.path.join(logging_dir,"bowtie_build.log"), "w")    
    cmd = [os.path.join(params.bin_dir,"bowtie-build"), 
        user_splice_fasta,
        user_splices_out_prefix]
    runExt(cmd=cmd,errString=desc)
    return user_splices_out_prefix

def check_bowtie_index(idx_prefix, chromo_dir, rerun, file_extension):
    desc = "Checking chromo_dir '%s' for Bowtie index files prefix '%s'" % (chromo_dir,idx_prefix)
    idx_fwd_1 = idx_prefix + ".1.ebwt"
    idx_fwd_2 = idx_prefix + ".2.ebwt"
    idx_fwd_3 = idx_prefix + ".3.ebwt"
    idx_fwd_4 = idx_prefix + ".4.ebwt"
    idx_rev_1 = idx_prefix + ".rev.1.ebwt"
    idx_rev_2 = idx_prefix + ".rev.2.ebwt"    
    if os.path.exists(idx_fwd_1) and \
        os.path.exists(idx_fwd_2) and \
        os.path.exists(idx_fwd_3) and \
        os.path.exists(idx_fwd_4) and \
        os.path.exists(idx_rev_1) and \
        os.path.exists(idx_rev_2) and \
        params.rerun == 0:
            return 
    logging.info(desc)    
    chromo_sequences = read_sequence_by_suffix(chromo_dir, file_extension)
    idx_prefix = build_chromosome_index(chromo_sequences, idx_prefix)
    idx_fwd_1 = idx_prefix + ".1.ebwt"
    idx_fwd_2 = idx_prefix + ".2.ebwt"
    idx_fwd_3 = idx_prefix + ".3.ebwt"
    idx_fwd_4 = idx_prefix + ".4.ebwt"
    idx_rev_1 = idx_prefix + ".rev.1.ebwt"
    idx_rev_2 = idx_prefix + ".rev.2.ebwt"    
    if os.path.exists(idx_fwd_1) and \
       os.path.exists(idx_fwd_2) and \
       os.path.exists(idx_fwd_3) and \
       os.path.exists(idx_fwd_4) and \
       os.path.exists(idx_rev_1) and \
       os.path.exists(idx_rev_2):
        return 
    else:
        logging.critical("Error: Could not find Bowtie index files %s.*" % idx_prefix)
        logging.shutdown()
        sys.exit(1)

def bowtie(bwt_idx_prefix,reads_list,reads_format,mapped_reads,unmapped_reads,bowtie_threads,seed_length,max_hits,
        unmapped_repeat_fasta_name,mismatch,log_file):
    """
    """
    start_time = datetime.now()
    bwt_idx_name = os.path.split(bwt_idx_prefix)[-1]
    desc = "Mapping reads against %s with Bowtie" % (bwt_idx_name)
    bwt_map = os.path.join(temp_dir,mapped_reads)
    unmapped_reads_fasta_name = os.path.join(temp_dir,unmapped_reads)    
    if os.path.exists(unmapped_reads_fasta_name) and os.path.exists(bwt_map) and params.rerun_all == 0:
        return (bwt_map, unmapped_reads_fasta_name)
    # Launch Bowtie
    cmd = [os.path.join(params.bin_dir,"bowtie")]	
    unmapped_format = "--un"	
    repeat_format = "--max"	
    if reads_format == "-q":
        unmapped_format = "--un"
        repeat_format = "--max"
    if mismatch > 3:
        mismatch = 3
    cmd += [reads_format,"--threads", str(bowtie_threads),unmapped_format, unmapped_reads_fasta_name,"-k", str(max_hits),"-v", str(mismatch),
        "--best",repeat_format, unmapped_repeat_fasta_name,bwt_idx_prefix,reads_list,bwt_map]   
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (bwt_map, unmapped_reads_fasta_name)

def bowtie2(bwt_idx_prefix,reads_list,reads_format,mapped_reads,unmapped_reads,bowtie_threads,seed_length,max_hits,
        unmapped_repeat_fasta_name,mismatch,log_file):
    bwt_idx_name = os.path.split(bwt_idx_prefix)[-1]
    desc = "Mapping reads against %s with Bowtie 2" % (bwt_idx_name)
    bwt_map = os.path.join(temp_dir,mapped_reads)
    unmapped_reads_fasta_name = os.path.join(temp_dir,unmapped_reads)    
    if os.path.exists(unmapped_reads_fasta_name) and os.path.exists(bwt_map) and params.rerun_all == 0:
        return (bwt_map, unmapped_reads_fasta_name)
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"bowtie")]
    unampped_format = "--unfa"
    repeat_format = "--maxfa"
    if reads_format == "-q":
        unampped_format = "--unfq"
        repeat_format = "--maxfq"
    if mismatch > 3:
        mismatch = 3
    cmd += [reads_format,"--threads", str(bowtie_threads),unampped_format, unmapped_reads_fasta_name,"-k", "0","-m", str(max_hits + 1),
    "-v", str(mismatch),repeat_format, unmapped_repeat_fasta_name, bwt_idx_prefix, reads_list,bwt_map]   
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (bwt_map, unmapped_reads_fasta_name)

def bowtie2sam(bowtie_mapped, misinfo, sam_formatted, log_file):
    desc = "Converting bowtie mapped to SAM format"
    if os.path.exists(sam_formatted) and params.rerun_all == 0:
        return sam_formatted
    logging.info(desc)    
    mapsplice_log = open(log_file, "w")
    cmd = [os.path.join(params.bin_dir,"bowtie2sam"), 
        bowtie_mapped,
        sam_formatted,
        str(misinfo)]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return sam_formatted

def FilterBWTByRegions(bowtie_mapped, regions, bowtie_mapped_in_regions, bowtie_mapped_notin_regions, log_file):
    desc = "Remove bwt mapped by regions" 
    if os.path.exists(bowtie_mapped_in_regions) and os.path.exists(bowtie_mapped_notin_regions) and params.rerun_all == 0:
        return (bowtie_mapped_in_regions, bowtie_mapped_notin_regions)
    logging.info(desc)        
    cmd = [os.path.join(params.bin_dir,"FilterBWTByRegions"), 
        regions,
        bowtie_mapped,
        bowtie_mapped_notin_regions,
        bowtie_mapped_in_regions]
    runExt(cmd=cmd,errString=desc,logFile=log_file)	
    return (bowtie_mapped_in_regions, bowtie_mapped_notin_regions)

def fa_fq_oneline(divided_reads, sorted_divide_reads, format_flag):
    desc = "fa_fq_oneline divide reads" 
    if os.path.exists(sorted_divide_reads) and params.rerun_all == 0:
        return sorted_divide_reads
    logging.info(desc)    
    if format_flag == "-f":
        line_per_reads = 2
    elif format_flag == "-q":
        line_per_reads = 4
    cmd = [os.path.join(params.bin_dir,"fa_fq_oneline"), 
        divided_reads,
        sorted_divide_reads,
        str(line_per_reads)]    
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return sorted_divide_reads

def cat_files(files_tobe_cat, cated_file):
    desc = "combine to final sam" 
    if os.path.exists(cated_file) and params.rerun_all == 0:
        return cated_file
    logging.info(desc)    
    cmd = ["cat"]
    for sam_file in files_tobe_cat:
       cmd.append(sam_file)
    cmd.append('>')
    cmd.append(cated_file)
    runExt(cmd=cmd,errString=desc)
    return cated_file

def merge_sort_segment_bwt1(tobe_sorted_1, tobe_sorted_2, merged_sorted):
    desc = "merge sort files"   
    if os.path.exists(merged_sorted) and params.rerun_all == 0:
        return merged_sorted
    logging.info(desc)        
    cmd = ["sort","-t~","-k1,1n","-S", "3500000", "-o", merged_sorted,"-T", temp_dir,tobe_sorted_1,tobe_sorted_2]    
    runExt(cmd=cmd,errString=desc)
    return merged_sorted

def merge_sort_segment_bwt2(tobe_sorted_1, merged_sorted):
    desc = "merge sort files by chromosome"    
    if os.path.exists(merged_sorted) and params.rerun_all == 0: 
        return merged_sorted
    logging.info(desc)    
    sam_cmd = ["sort","-k2,2","-k4,4n","-S", "3500000", "-o", merged_sorted,"-T", temp_dir,tobe_sorted_1]    
    runExt(cmd=cmd,errString=desc)
    return merged_sorted

def sort_segment_bwt1(segment_bwt, segment_bwt_sorted):
    desc = "sort segmentbwt 1"   
    if os.path.exists(segment_bwt_sorted) and params.rerun_all == 0:
        return segment_bwt_sorted
    logging.info(desc)        
    cmd = ["sort","-t~","-k1,1n", "-S", "3500000", "-o", segment_bwt_sorted,  "-T", temp_dir,segment_bwt]    
    runExt(cmd=cmd,errString=desc)
    temp_fs = open(segment_bwt, "w")
    temp_fs.close()
    return segment_bwt_sorted

def sort_segment_bwt(segment_bwt, segment_bwt_sorted):
    desc = "sort segmentbwt"
    if os.path.exists(segment_bwt_sorted) and params.rerun_all == 0:
        temp_fs = open(segment_bwt, "w")
        temp_fs.close()
        return segment_bwt_sorted
    logging.info(desc)           
    cmd = ["sort", "-t~","-k2,2n","-S", "3500000","-o", segment_bwt_sorted,"-T", temp_dir,segment_bwt]    
    runExt(cmd=cmd,errString=desc)
    temp_fs = open(segment_bwt, "w")
    temp_fs.close()
    return segment_bwt_sorted

def sort_by_name(segment_bwt, segment_bwt_sorted):
    desc = "sort by name"   
    if os.path.exists(segment_bwt_sorted) and params.rerun_all == 0:
        temp_fs = open(segment_bwt, "w")
        temp_fs.close()
        return segment_bwt_sorted
    logging.info(desc) 
    cmd = ["sort","-t~","-k2,2","-S", "3500000","-o", segment_bwt_sorted, "-T", temp_dir,segment_bwt]    
    runExt(cmd=cmd,errString=desc)	
    temp_fs = open(segment_bwt, "w")
    temp_fs.close()
    return segment_bwt_sorted

def sort_by_name1(segment_bwt, segment_bwt_sorted):
    """ NOTE lack of ~ as the separator for this sort? Presumably a space delimited file?"""
    desc = "sort by name 1"   
    if os.path.exists(segment_bwt_sorted) and params.rerun_all == 0:
        temp_fs = open(segment_bwt, "w")
        temp_fs.close()
        return segment_bwt_sorted
    logging.info(desc)
    cmd = ["sort","-k1,1", "-S", "3500000","-o", segment_bwt_sorted, "-T", temp_dir, segment_bwt]    
    runExt(cmd=cmd,errString=desc)
    temp_fs = open(segment_bwt, "w")
    temp_fs.close()
    return segment_bwt_sorted

def mapsplice_search(min_intron, max_intron, seg_len, ext_len, sorted_read_file, format_flag, chrom_size_file, 
        whole_reads_bwt, island_ext, island_gap, island_output, segment_bwt, pairend, max_insert):
    desc = "mapsplice_search"  
    if os.path.exists(island_output) and params.rerun_all == 0:
        return island_output
    logging.info(desc)
    read_format = ""
    if format_flag == "-f":
        read_format = "-fa"
    elif format_flag == "-q":
        read_format = "-fq"
    cmd = [os.path.join(params.bin_dir,"mapsplice_search"),"--max_insertion", str(max_insert),"-i", str(min_intron),"-I", str(max_intron),
        "-l", str(seg_len),"-e", str(ext_len),"-ie", str(island_ext),"-g", str(island_gap),"-r", str(sorted_read_file),"-m", str(whole_reads_bwt),
        "-c", str(chrom_size_file),"-o1", hole_dir,"-o2", hmer_dir,"-o3", head_dir,"-o4", tail_dir,"-o5", island_output,read_format]
    if pairend <> "":
        cmd.append("-pe")	
    cmd.append(segment_bwt)
    runExt(cmd=cmd,errString=desc)
    return island_output

def mapsplice_report(seg_len, chrom_size_file, ext_bit, sorted_read, format_flag, unspliced_mapped_segment, 
        max_intron, fusion_file, single_sam_file, paired_sam_file, min_seg, min_fusion_seg, do_fusion, paired):
    desc = "mapsplice_report"
    if os.path.exists(single_sam_file) and params.rerun_all == 0:
        return single_sam_file
    logging.info(desc)
    formatfq = "-fq"
    if format_flag == "-f":
        formatfq = "-fa"    
    cmd = [os.path.join(params.bin_dir,"mapsplice_report"),"-l", str(seg_len),"-c", chrom_size_file,"-e", str(ext_bit),"-r", sorted_read,
        "-s", str(min_seg),"-I", str(max_intron),formatfq,"-i1", unspliced_mapped_segment,"-i2", hole_dir,"-i3", hmer_dir,"-i4", head_dir,
        "-i5", tail_dir,"-o", single_sam_file]    
    if paired_sam_file <> "":
        cmd += ["-o2", paired_sam_file,"-o3", paired_sam_file + ".filtered"]    
    if paired <> "":
        cmd.append("-pe")
    if do_fusion == 1: 
        cmd += ["-f", fusion_dir]# + ["-v", str(min_fusion_seg)]
    runExt(cmd=cmd,errString=desc)
    return single_sam_file

def RemDup(syn_mapped, syn_mapped_remdup_unique_spliced, syn_mapped_remdup_multiple_spliced, stat_file, log_file): 
    desc = "Remove duplication of sam" 
    if os.path.exists(syn_mapped_remdup_unique_spliced) and  os.path.exists(syn_mapped_remdup_multiple_spliced) and params.rerun_all == 0:
        return (syn_mapped_remdup_unique_spliced, syn_mapped_remdup_multiple_spliced)    
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"RemDup"),syn_mapped,syn_mapped_remdup_unique_spliced] 
    cmd += [syn_mapped_remdup_multiple_spliced,stat_file]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (syn_mapped_remdup_unique_spliced, syn_mapped_remdup_multiple_spliced)

def SepSplicedUnSpliced(combined_sam, spliced_sam, unspliced_sam, stat_file, log_file): #syn_mapped_remdup_unspliced, 
    desc = "Separate Spliced UnSpliced sam" 
    if os.path.exists(spliced_sam) and os.path.exists(unspliced_sam) and params.rerun_all == 0:
        return (spliced_sam, unspliced_sam)
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"SepSplicedUnspliced"),combined_sam,spliced_sam,unspliced_sam,stat_file]#[syn_mapped_remdup_unspliced] + 
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (spliced_sam, unspliced_sam)

def FilterByParing(tobepairedsam, pairedsam, fusionpairedsam, singlesam, filteredsam, max_dist, stat_file, log_file):
    desc = "filter by pairing"
    if os.path.exists(pairedsam) and os.path.exists(filteredsam) and params.rerun_all == 0:
        return (pairedsam, filteredsam)
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"pairing"),tobepairedsam,pairedsam,fusionpairedsam,singlesam,filteredsam]
    cmd += [stat_file,str(max_dist)]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (pairedsam, filteredsam)

def FilterReadsByCanonNoncanon(syn_mapped_remdup, junc_file, filtered_canon, filtered_noncanon, filtered_noncanon_canon, 
        filtered_ins, stat_file, log_file):
    desc = "Filter Reads By Canon Noncanon"
    if os.path.exists(filtered_canon) and os.path.exists(filtered_noncanon) and os.path.exists(filtered_noncanon_canon) and params.rerun_all == 0:
        return (filtered_canon, filtered_noncanon, filtered_noncanon_canon)
    logging.info(desc)    
    cmd = [os.path.join(params.bin_dir,"FilterReadsByCanonNoncanonByReads"),syn_mapped_remdup,junc_file,filtered_canon,filtered_noncanon,
        filtered_noncanon_canon,filtered_ins,stat_file]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return (filtered_canon, filtered_noncanon, filtered_noncanon_canon)

def juncdb_bwt2sam(bowtie_mapped, misinfo, sam_formatted, log_file):
    desc = "Converting juncdb bowtie mapped to SAM format"    
    if os.path.exists(sam_formatted) and params.rerun_all == 0:
        return sam_formatted
    logging.info(desc)
    cmd = [os.path.join(params.bin_dir,"juncdb_bwt2sam"),bowtie_mapped,sam_formatted,str(misinfo)] 
    runExt(cmd=cmd,errString=desc,logFile=log_file)    
    return sam_formatted

def juncdb_fusion_bwt2sam(bowtie_mapped, misinfo, sam_formatted, syn_len, log_file):
    desc = "Converting fusion juncdb bowtie mapped to SAM format"
    if os.path.exists(sam_formatted) and params.rerun_all == 0:
        return sam_formatted
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"juncdb_fusion_bwt2sam"),bowtie_mapped,sam_formatted,str(syn_len),str(misinfo)] 
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return sam_formatted

def replace_fusion_seq(bowtie_mapped, bowtie_mapped_replaced, synthe_fusion_file, log_file):
    desc = "Replace fusion read sequence with syn chromosome sequence"
    if os.path.exists(bowtie_mapped_replaced) and params.rerun_all == 0:
        return bowtie_mapped_replaced
    logging.info(desc)   
    cmd = [os.path.join(params.bin_dir,"replace_fusion_seq"),bowtie_mapped,bowtie_mapped_replaced,synthe_fusion_file] 
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return bowtie_mapped_replaced

def dividereads(reads_files, seg_len, format_flag):
    desc = "divide reads" 
    log_file = open(params.logging_dir + "dividereads.log", "w")
    divided_reads = os.path.join(temp_dir, "divided_reads.fa")    
    divided_reads_trunc = os.path.join(temp_dir,"divided_reads_trunc.fa")    
    if os.path.exists(divided_reads) and params.rerun_all == 0:         
        return divided_reads
    logging.info(desc) 
    read_files_array = reads_files.split(',')    
    dividereads_cmd = [os.path.join(params.bin_dir,"dividereads"),]
    dividereads_cmd += read_files_array    
    formatf = '1'
    if format_flag == "-q":
        formatf = '0'
    cmd += [divided_reads_trunc,divided_reads,formatf,str(seg_len)]   
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return divided_reads

def dividereadsindexed(reads_files, seg_len, format_flag):
    desc = "divide reads" 
    log_file = os.path.join(params.logging_dir,"dividereads.log")  
    divided_reads = os.path.join(temp_dir,"divided_reads.fa")    
    divided_reads_trunc = os.path.join(temp_dir,"divided_reads_trunc.fa")    
    if os.path.exists(divided_reads) and params.rerun_all == 0:
        return divided_reads
    logging.info(desc)     
    read_files_array = reads_files.split(',')    
    cmd = [os.path.join(params.bin_dir,"dividereadsindexed"),]
    cmd += read_files_array    
    formatf = '1'
    if format_flag == "-q":
        formatf = '0'
    cmd += [divided_reads_trunc,divided_reads,formatf,str(seg_len)]
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return divided_reads

def remove_index_sam(indexed_sam_file, remove_indexed_sam_file):
    desc = "remove index of sam" 
    if os.path.exists(remove_indexed_sam_file) and params.rerun_all == 0:
        return remove_indexed_sam_file    
    logging.info(desc) 
    cmd = [os.path.join(params.bin_dir,"remove_index_sam"),indexed_sam_file,remove_indexed_sam_file]
    runExt(cmd=cmd,errString=desc)
    return remove_indexed_sam_file

def merge_paired_end_reads(reads_files, format_flag, paired, merged_reads):
    desc = "merge paired end reads" 
    if os.path.exists(merged_reads) and params.rerun_all == 0:
        return merged_reads 
    logging.info(desc)    
    read_files_array = reads_files.split(',')  
    cmd = [os.path.join(params.bin_dir,"merge_paired_end_reads")]
    cmd += read_files_array
    format_int = '1'
    if format_flag == "-q":
        format_int = '0'
    ispaired = '0'
    if paired != "":
        ispaired = '1'
    cmd += [ispaired,format_int,merged_reads] 
    runExt(cmd=cmd,errString=desc)   
    return merged_reads

def merge_paired_end_reads_rmshort(reads_files, format_flag, paired, seg_len, merged_reads):
    desc = "merge paired end reads remove short"  
    if os.path.exists(merged_reads) and params.rerun_all == 0:
        return merged_reads
    logging.info(desc)    
    read_files_array = reads_files.split(',')  
    cmd = [os.path.join(params.bin_dir,"merge_paired_end_reads_rmshort")]
    cmd += read_files_array
    format_int = '1'
    if format_flag == "-q":
        format_int = '0'
    ispaired = '0'
    if paired != "":
        ispaired = '1'
    cmd += [str(seg_len),ispaired,format_int,merged_reads] 
    runExt(cmd=cmd,errString=desc)   
    return merged_reads 

def check_reads_format(reads_files, format_flag, paired):    
    desc = "check reads format"  
    logging.info(desc)    
    read_files_array = reads_files.split(',')  
    cmd = [os.path.join(params.bin_dir,"check_reads_format")]
    cmd += read_files_array
    format_int = '1'
    if format_flag == "-q":
        format_int = '0'
    ispaired = '0'
    if paired != "":
        ispaired = '1'
    cmd += ['0',ispaired,format_int] 
    runExt(cmd=cmd,errString=desc,logFile="check_reads_format.log")   
    
def index_reads(reads_files, format_flag, merged_reads):
    desc = "index reads" 
    logging.info(desc)    
    read_files_array = reads_files.split(',')  
    cmd = [os.path.join(params.bin_dir,"index_reads")]
    cmd += read_files_array
    format_int = '1'
    if format_flag == "-q":
        format_int = '0'
    cmd += [format_int,merged_reads] 
    runExt(cmd=cmd,errString=desc,logFile="index_reads.log") 
    return merged_reads

def parsepileup(pileup_file, threshold, boundary):
    desc = "Parsing pileup file"
    islands_file = os.path.join(temp_dir, "islands.gff")    
    if os.path.exists(islands_file) and params.rerun_all == 0:
        temp_fs = open(pileup_file, "w")
        temp_fs.close()
        return islands_file
    logging.info(desc)  
    cmd = [os.path.join(params.bin_dir,"parsepileup"), pileup_file, islands_file,str(threshold), str(boundary), temp_dir]            
    runExt(cmd=cmd,errString=desc) 
    temp_fs = open(pileup_file, "w")
    temp_fs.close()    
    return islands_file

def merge_comb_bowtie(bowtiefile, sortedbowtie, maximal_intron, readsfile,
        chromdir, num_seg, seg_len, merged_bowtie):
    desc = "Merging combine bowtie file"
    cmd = [os.path.join(params.bin_dir,"merge_comb_bowtie"), bowtiefile, sortedbowtie, str(maximal_intron), 
        readsfile, chromdir, str(num_seg), str(seg_len), merged_bowtie]
    if os.path.exists(merged_bowtie) and os.path.exists(sortedbowtie) and params.rerun_all == 0:
        temp_fs = open(bowtiefile + ".notcombined", "w")
        temp_fs.close()
        return bowtiefile
    logging.info(desc)
    runExt(cmd=cmd,errString=desc) 
    temp_fs = open(bowtiefile + ".notcombined", "w")
    temp_fs.close()    
    return bowtiefile

def merge_sam(bowtie_mapped_sam, bowtie_mapped_sam_25):
    desc = "Merging bowtie sam file"
    merged_bam = os.path.join(temp_dir,"merged.sam")
    if os.path.exists(merged_bam) and params.rerun_all == 0:
        temp_fs = open(bowtie_mapped_sam, "w")
        temp_fs.close()
        temp_fs = open(bowtie_mapped_sam_25, "w")
        temp_fs.close()
        return merged_bam    
    cmd = [os.path.join(params.bin_dir,"merge_sam"), bowtie_mapped_sam, bowtie_mapped_sam_25, merged_bam]  
    logging.info(desc)
    runExt(cmd=cmd,errString=desc)
    temp_fs = open(bowtie_mapped_sam, "w")
    temp_fs.close()
    temp_fs = open(bowtie_mapped_sam_25, "w")
    temp_fs.close()
    return merged_bam

def merge_chromo_sams(all_sams_path, merged_sam, log_file):
    desc = "Merging all sam files"     
    if os.path.exists(merged_sam) and params.rerun_all == 0:
        return merged_sam
    cmd = [os.path.join(params.bin_dir,"merge_sam")]
    cmd += all_sams_path
    cmd.append(merged_sam)
    logging.info(desc)
    runExt(cmd=cmd,errString=desc,logFile=log_file)
    return merged_sam

def read_chromo_sizes(all_sams_path, chromo_size_file, chrom_names):
    desc = "reads all chromo sizes"    
    if os.path.exists(chromo_size_file) and os.path.exists(chrom_names) and params.rerun_all == 0:
        return chromo_size_file
    cmd = [os.path.join(params.bin_dir,"read_chromo_size"),] 
    cmd += all_sams_path 
    cmd += [chromo_size_file]
    cmd += [chrom_names]
    logging.info(desc)
    runExt(cmd=cmd,errString=desc)
    return chromo_size_file


def format_reads_func(reads_file, formated_reads_file):
    desc = "format reads"
    cmd = [os.path.join(params.bin_dir,"remove_blankspace_perline"),]  
    cmd += [reads_file]
    cmd += [formated_reads_file]
    logging.info(desc)
    runExt(cmd=cmd,errString=desc,logFile="format_reads.log")
    return formated_reads_file

def sam2fq(sam_formatted, converted_read_file, flag, log_file):
    desc = "convert sam to fq reads"
    cmd = [os.path.join(params.bin_dir,"sam2fq"),]  
    cmd += [converted_read_file]
    cmd += [flag]
    cmd += read_files_array
    cmd = [os.path.join(params.bin_dir,"remove_blankspace_perline"),]  
    cmd += [reads_file]
    cmd += [formated_reads_file]
    logging.info(desc)
    runExt(cmd=cmd,errString=desc,logFile="format_reads.log")
    return converted_read_file

def sam2fq_array(sam_formatted, converted_read_file, flag, log_file):
    print >> sys.stderr, "[%s] convert sam to fq reads" % (right_now())
    
    mapsplice_log = open(log_file, "w")
   
    merge_sam_cmd = [bin_dir + "sam2fq"]  

    merge_sam_cmd = merge_sam_cmd + [converted_read_file]
    
    merge_sam_cmd = merge_sam_cmd + [flag]
    
    read_files_array = sam_formatted.split(',')

    for read_file in read_files_array:
	merge_sam_cmd = merge_sam_cmd + [read_file]

    if DEBUG == 1:
	print >> sys.stderr, "[%s] " % merge_sam_cmd
	
    try:    
        retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: convert sam to fq reads failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: sam2fq not found on this system"
        exit(1)
	
    return converted_read_file

def bam2sam(bam_file, sam_file):
    print >> sys.stderr, "[%s] convert bam to sam" % (right_now())
    
    mapsplice_log = open(sam_file, "w")
   
    merge_sam_cmd = [bin_dir + "samtools"]  

    merge_sam_cmd = merge_sam_cmd + ["view"]

    merge_sam_cmd = merge_sam_cmd + [bam_file]
    
    if DEBUG == 1:
	print >> sys.stderr, "[%s] " % merge_sam_cmd
	
    try:    
        retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: convert bam to sam failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: samtools not found on this system"
        exit(1)
	
    return sam_file

def format_chromos_func(all_chroms_path):
    print >> sys.stderr, "[%s] format chromosome files" % (right_now())
    
    #print >> sys.stderr, "[%s] " % all_chroms_path
   
    merge_sam_cmd = [bin_dir + "remove_blankspace"]  
    
    mapsplice_log = open(logging_dir + "format_chromos.log", "w")
    #stdout=mapsplice_log
    
    for sam_file in all_chroms_path:
	merge_sam_cmd = merge_sam_cmd + [sam_file]
    
    merge_sam_cmd = merge_sam_cmd + [formated_chrom_dir]
    
    #print >> sys.stderr, "[%s] format chromosomes" % merge_sam_cmd
    
    #print >> sys.stderr, "[%s] Merging all sams file" % merge_sam_cmd
    try:    
        retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: format chromosomes failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: remove_blankspace not found on this system"
        exit(1)
	
    return formated_chrom_dir

def merge_sam_cut_alters(unspliced_sam, spliced_sam, merged_sam):
    print >> sys.stderr, "[%s] Merging bowtie sam file cut alters" % (right_now())

    if os.path.exists(merged_sam) and \
	   params.rerun_all == 0:
	return merged_sam
    
    merge_sam_cmd = [bin_dir + "merge_sam_cutalters", unspliced_sam, spliced_sam, merged_sam]  
    try:    
        retcode = subprocess.call(merge_sam_cmd)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: merge bowtie cut alters failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: merge_sam_cutalters not found on this system"
        exit(1)
	
    return merged_sam

def pileup2wig(pileupfile, wigfile, allchromos_fai):
    print >> sys.stderr, "[%s] convert pileup to wig file" % (right_now())

    if os.path.exists(wigfile) and \
	   params.rerun_all == 0:
	temp_fs = open(pileupfile, "w")
	temp_fs.close()
	return wigfile
    
    merge_sam_cmd = [bin_dir + "pileup2wig", pileupfile, wigfile, allchromos_fai]  
    try:    
        retcode = subprocess.call(merge_sam_cmd)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: convert pileup to wig file failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: pileup2wig not found on this system"
        exit(1)
    
    temp_fs = open(pileupfile, "w")
    temp_fs.close()
    
    return wigfile

def sam2pileup(bowtie_mapped_sam, allchromos_file):
    print >> sys.stderr, "[%s] Converting bowtie sam file to pileup format" % (right_now())

    pileup_file = bowtie_mapped_sam + ".pileup"
    
    bowtie_mapped_bam = bowtie_mapped_sam + ".bam"
    
    bowtie_mapped_bam_sorted = bowtie_mapped_bam + ".sorted"
    
    bowtie_mapped_bam_sorted_bam = bowtie_mapped_bam_sorted + ".bam"
    
    allchromos_file_fai = allchromos_file + ".fai"
    
    if os.path.exists(pileup_file) and \
	   params.rerun_all == 0:
	temp_fs = open(bowtie_mapped_sam, "w")
	temp_fs.close()
	if os.path.exists(bowtie_mapped_bam):
	    temp_fs = open(bowtie_mapped_bam, "rw")
	    temp_fs.close()
	if os.path.exists(bowtie_mapped_bam_sorted_bam):
	    temp_fs = open(bowtie_mapped_bam_sorted_bam, "rw")
	    temp_fs.close()
	return pileup_file
    
    pileup_fs = open(pileup_file, "w")
    

    
    sam2pileup_cmd = ""
    if bowtie_mapped_sam.endswith(".sam"):
	sam2faidx_cmd = [bin_dir + "samtools", "faidx", allchromos_file]
	
	try:    
	    retcode = subprocess.call(sam2faidx_cmd)
	    
	    if retcode > 0:
		print >> sys.stderr, fail_str, "Error: faidx allchromos_file failed"
		exit(1)
		
	except OSError, o:
	    if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
		print >> sys.stderr, fail_str, "Error: samtools not found on this system"
	    exit(1)
	    
	
	
    	sam2import_cmd = [bin_dir + "samtools", "import", allchromos_file_fai,
                      	bowtie_mapped_sam, bowtie_mapped_bam]
	
	try:    
	    retcode = subprocess.call(sam2import_cmd)
       
	    if retcode > 0:
		print >> sys.stderr, fail_str, "Error: import sam to bam failed"
		exit(1)
	
	except OSError, o:
	    if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
		print >> sys.stderr, fail_str, "Error: samtools not found on this system"
	    exit(1)
	    
	temp_fs = open(bowtie_mapped_sam, "w")
	temp_fs.close()

	sam2sort_cmd = [bin_dir + "samtools", "sort", bowtie_mapped_bam, bowtie_mapped_bam_sorted]
	
	try:    
	    retcode = subprocess.call(sam2sort_cmd)
       
	    if retcode > 0:
		print >> sys.stderr, fail_str, "Error: sort bam failed"
		exit(1)

	except OSError, o:
	    if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
		print >> sys.stderr, fail_str, "Error: samtools not found on this system"
	    exit(1)
	    
	temp_fs = open(bowtie_mapped_bam, "w")
	temp_fs.close()
	
    elif bowtie_mapped_sam.endswith(".bam"):
	bowtie_mapped_bam_sorted_bam = bowtie_mapped_sam
	
    
    sam2pileup_cmd = [bin_dir + "samtools", "pileup",
                     "-f", allchromos_file,
                     bowtie_mapped_bam_sorted_bam, ">", pileup_file]
    try:    
        retcode = subprocess.call(sam2pileup_cmd, stdout=pileup_fs)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: convert bowtie sam to pileup failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: samtools not found on this system"
        exit(1)
	
    temp_fs = open(bowtie_mapped_bam_sorted_bam, "w")
    temp_fs.close()
    
    return pileup_file

def synthetic_junc(junc_file, chromosome_files_dir, read_width, anchor_width):
    print >> sys.stderr, "[%s] Synthetic junctions" % (right_now())
    
    chromosome_files_dir = chromosome_files_dir + "/"
    
    synjunc_log = open(logging_dir + "synjunc.log", "w")
    
    syn_junction = output_dir + "syn_junctions.txt"
    
    syn_junc_cmd = [bin_dir + "synjunc", junc_file, 
                        syn_junction, str(read_width - anchor_width), chromosome_files_dir]            
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=synjunc_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Synthetic junctions failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: synjunc not found on this system"
        exit(1)
    return syn_junction

def syn_fusion_junc_seq(junc_file, syn_junc_file, chromosome_files_dir, synlen, log_file):
    print >> sys.stderr, "[%s] Synthetic fusion junctions sequence" % (right_now())
    
    if os.path.exists(syn_junc_file) and \
	   params.rerun_all == 0:
	return syn_junc_file
    
    chromosome_files_dir = chromosome_files_dir + "/"
    
    synjunc_log = open(log_file, "w")
    
    syn_junction = syn_junc_file
    
    syn_junc_cmd = [bin_dir + "syn_fusion_junc_seq", junc_file, 
                        syn_junc_file, chromosome_files_dir, str(synlen)]            
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=synjunc_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Synthetic fusion junctions sequence"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: syn_fusion_junc_seq not found on this system"
        exit(1)
    return syn_junction

def FusionBWA2FusionSam(fusion_BWT_file, fusion_SAM_file, synlen, log_file):
    print >> sys.stderr, "[%s] Convert fusion bwt to sam" % (right_now())
    
    if os.path.exists(fusion_SAM_file) and \
	   params.rerun_all == 0:
	return fusion_SAM_file
    
    synjunc_log = open(log_file, "w")

    syn_junc_cmd = [bin_dir + "FusionBWA2FusionSam", fusion_BWT_file, 
                        fusion_SAM_file, str(synlen)]            
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=synjunc_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Convert fusion bwt to sam"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: FusionBWA2FusionSam not found on this system"
        exit(1)
    return fusion_SAM_file

def FusionBWA2FusionSamNew(fusion_BWT_file, fusion_SAM_file, synlen, log_file):
    print >> sys.stderr, "[%s] Convert fusion bwt to sam" % (right_now())
    
    if os.path.exists(fusion_SAM_file) and \
	   params.rerun_all == 0:
	return fusion_SAM_file
    
    synjunc_log = open(log_file, "w")

    syn_junc_cmd = [bin_dir + "FusionBWA2FusionSam", fusion_BWT_file, 
                        fusion_SAM_file, str(synlen)]            
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=synjunc_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Convert fusion bwt to sam"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: FusionBWA2FusionSam not found on this system"
        exit(1)
    return fusion_SAM_file

def FilterSamByJunc(all_sams_path, junc_bed, remained_sam, filtered_sam, log_file):
    print >> sys.stderr, "[%s] Filter Sam By junction" % (right_now())
    
    if os.path.exists(remained_sam) and \
       os.path.exists(filtered_sam) and \
	   params.rerun_all == 0:
	return (remained_sam, filtered_sam)
    
    mapsplice_log = open(log_file, "w")
    #stdout=mapsplice_log
    
    merge_sam_cmd = [bin_dir + "FilterSamByJunc"] + [junc_bed] + [remained_sam] + [filtered_sam]
   
    for sam_file in all_sams_path:
	merge_sam_cmd = merge_sam_cmd + [sam_file]
   
    #print >> sys.stderr, "[%s] Merging all sams file" % merge_sam_cmd
    try:    
        retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Filter Sam By junction failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: FilterSamByJunc not found on this system"
        exit(1)
	
    return (remained_sam, filtered_sam)

def AddTagsToSam(sam_file, added_tags_sam_file, paired, reads_file, unmapped_sam, stat_file, format_flag, max_insert, junction, chrom_size, log_file):
    print >> sys.stderr, "[%s] Add tags to sam file" % (right_now())
    
    if os.path.exists(added_tags_sam_file) and \
       os.path.exists(unmapped_sam) and \
	   params.rerun_all == 0:
	return (added_tags_sam_file, unmapped_sam)
    
    mapsplice_log = open(log_file, "w")
    #stdout=mapsplice_log
    
    merge_sam_cmd = [bin_dir + "AddTagsToSam"] + [sam_file] + [added_tags_sam_file] + [stat_file]

    ispaired = 0
    
    if paired != "":
	ispaired = 1
	
    cmd_format = "fa"
    
    if format_flag == '-q':
	cmd_format = "fq"
	
    merge_sam_cmd = merge_sam_cmd + [str(ispaired)] + [reads_file] + [unmapped_sam] + [cmd_format] + [str(max_insert)] + [junction] + [chrom_size]
   
    if DEBUG == 1:
	print >> sys.stderr, "[%s] AddTagsToSam" % merge_sam_cmd
	
    try:    
        retcode = subprocess.call(merge_sam_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Add tags to sam file failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: AddTagsToSam not found on this system"
        exit(1)
	
    return (added_tags_sam_file, unmapped_sam)

def junc_db(junc_file, chromosome_files_dir, min_anchor_width, max_anchor, max_threshold, synthetic_file, log_file):
    print >> sys.stderr, "[%s] Synthetic junctions sequence" % (right_now())
    
    if os.path.exists(synthetic_file) and \
	   params.rerun_all == 0:
	return synthetic_file
    
    chromosome_files_dir = chromosome_files_dir + "/"
    
    syn_junc_cmd = [bin_dir + "junc_db", str(min_anchor_width), str(max_anchor), str(max_threshold),
                        junc_file, chromosome_files_dir, synthetic_file]
    
    if DEBUG == 1:
	print >> sys.stderr, "[%s]" % syn_junc_cmd
    
    mapsplice_log = open(log_file, "w")
    #stdout=mapsplice_log
    
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Synthetic junctions sequence failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: junc_db not found on this system"
        exit(1)
    return synthetic_file

def fusion_junc_db(junc_file, fusion_junc_file, chromosome_files_dir, min_anchor_width, 
                   max_anchor, max_threshold, synthetic_file, log_file):
    print >> sys.stderr, "[%s] Synthetic fusion junctions sequence" % (right_now())
    
    if os.path.exists(synthetic_file) and \
	   params.rerun_all == 0:
	return synthetic_file
    
    chromosome_files_dir = chromosome_files_dir + "/"
    
    syn_junc_cmd = [bin_dir + "junction_database_fusion", str(min_anchor_width), str(max_anchor), str(max_threshold),
                        junc_file, fusion_junc_file, chromosome_files_dir, synthetic_file]
    
    if DEBUG == 1:
	print >> sys.stderr, "[%s]" % syn_junc_cmd
    
    mapsplice_log = open(log_file, "w")
    #stdout=mapsplice_log
    
    try:    
        retcode = subprocess.call(syn_junc_cmd, stdout=mapsplice_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Synthetic fusion junctions sequence failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: junction_database_fusion not found on this system"
        exit(1)
    return synthetic_file

def compare_junc(f1_junc, f2_junc, compare_range, cur_out_dir):
    print >> sys.stderr, "[%s] compare juncitons" % (right_now())
   
    basename = os.path.basename(f1_junc)
    filename = os.path.splitext(basename)
    f1_basename = filename[0]
    
    basename = os.path.basename(f2_junc)
    filename = os.path.splitext(basename)
    f2_basename = filename[0]
    
    if os.path.exists(cur_out_dir):
	pass
    else:        
	os.mkdir(cur_out_dir)
    
    in_f1_and_in_f2 = cur_out_dir + "in_(" + f1_basename + ")_in_(" + f2_basename + ").txt"
    in_f1_not_in_f2 = cur_out_dir + "in_(" + f1_basename + ")_NOTin_(" + f2_basename + ").txt"
    in_f2_not_in_f1 = cur_out_dir + "in_(" + f2_basename + ")_NOTin_(" + f1_basename + ").txt"
    
    compare_junc_cmd = ["mono", bin_dir + "compare_junc.exe", "-h1", "-h2", "-o", cur_out_dir, "-s", "-m", str(compare_range), 
			      f1_junc, f2_junc]            
    try:    
        retcode = subprocess.call(compare_junc_cmd)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: compare juncitons failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error:compare_junc.exe not found on this system"
        exit(1)
    return (in_f1_not_in_f2, in_f2_not_in_f1, in_f1_and_in_f2)

def filter_by_expression_level(junc_file, gamma, delta):
    print >> sys.stderr, "[%s] Filtering junction by expression level format" % (right_now())

    filtered_junction = output_dir + "junctions_filtered.txt"
    
    fel_log = open(logging_dir + "filter_byexpresslevel.log", "w")
    
    filter_50bp_cmd = [bin_dir + "filterjuncbyexpresslevel", junc_file, 
                       filtered_junction, str(gamma), str(delta), output_dir]            
    try:    
        retcode = subprocess.call(filter_50bp_cmd, stdout=fel_log)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: Filtering junction by expression level failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: filterbyexpresslevel not found on this system"
        exit(1)
    return filtered_junction

def filterbyanchor(junction, min_anchor, read_width, filtered, notfiltered):
    print >> sys.stderr, "[%s] filter by anchor length" % (right_now())
    
    if os.path.exists(filtered) and \
           os.path.exists(notfiltered)  and \
	   params.rerun_all == 0:
	return (filtered, notfiltered)
        
    filterbyintronlen_cmd = [bin_dir + "filterjuncbyanchor", junction, filtered, notfiltered, str(min_anchor), str(read_width)]            
    try:    
        retcode = subprocess.call(filterbyintronlen_cmd)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: filter by anchor length failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: filterjuncbyanchor not found on this system"
        exit(1)
	
    return (filtered, notfiltered)

def filternotinisland(island, junction, notinisland, inisland):
    print >> sys.stderr, "[%s] filter by island" % (right_now())
    
    if os.path.exists(notinisland) and \
           os.path.exists(inisland)  and \
	   params.rerun_all == 0:
	return (notinisland, inisland)
    
    filternotinisland_cmd = [bin_dir + "filternotinisland", island, junction, 
			     notinisland, inisland]
    try:    
        retcode = subprocess.call(filternotinisland_cmd)
       
        if retcode > 0:
            print >> sys.stderr, fail_str, "Error: filter by island failed"
            exit(1)
    except OSError, o:
        if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
            print >> sys.stderr, fail_str, "Error: filternotinislands not found on this system"
        exit(1)
	
    return (notinisland, inisland)

def process_extsam(samfile, outputjuncname, cur_out_dir, min_intron_length, max_intron_length, min_anchor, chromosome_files_dir, read_width):
    print >> sys.stderr, "[%s] process external sam file" % (right_now())
    
    sam2junc1(samfile, cur_out_dir + outputjuncname, 
	 chromosome_files_dir, read_width, 1, 100000000, "", 1)
    
    sam2junc1(samfile, cur_out_dir + outputjuncname + ".in_intron", 
	 chromosome_files_dir, read_width, min_intron_length, max_intron_length, "", 1)
    
    separate_canon_noncanon(cur_out_dir + outputjuncname + ".in_intron",
			    cur_out_dir + outputjuncname + ".in_intron" + ".canon",
			    cur_out_dir + outputjuncname + ".in_intron" + ".noncanon")
    
    sam2junc1(samfile, cur_out_dir + outputjuncname + ".exceed_intron", 
	 chromosome_files_dir, read_width,max_intron_length+1, 100000000, "", 1)
    
    separate_canon_noncanon(cur_out_dir + outputjuncname + ".exceed_intron",
			    cur_out_dir + outputjuncname + ".exceed_intron" + ".canon",
			    cur_out_dir + outputjuncname + ".exceed_intron" + ".noncanon")
    
    sam2junc1(samfile, cur_out_dir + outputjuncname + ".in_intron.anchor", 
	 chromosome_files_dir, read_width, min_intron_length, max_intron_length, "", min_anchor)
    
    separate_canon_noncanon(cur_out_dir + outputjuncname + ".in_intron.anchor",
			    cur_out_dir + outputjuncname + ".in_intron.anchor" + ".canon",
			    cur_out_dir + outputjuncname + ".in_intron.anchor" + ".noncanon")
    
    sam2junc1(samfile, cur_out_dir + outputjuncname + ".exceed_intron.anchor", 
	 chromosome_files_dir, read_width,max_intron_length+1, 100000000, "", min_anchor)
    
    separate_canon_noncanon(cur_out_dir + outputjuncname + ".exceed_intron.anchor",
			    cur_out_dir + outputjuncname + ".exceed_intron.anchor" + ".canon",
			    cur_out_dir + outputjuncname + ".exceed_intron.anchor" + ".noncanon")
    
    return (cur_out_dir + outputjuncname + ".in_intron" + ".canon",
	    cur_out_dir + outputjuncname + ".in_intron" + ".noncanon",
	    cur_out_dir + outputjuncname + ".exceed_intron" + ".canon",
	    cur_out_dir + outputjuncname + ".exceed_intron" + ".noncanon",
	    cur_out_dir + outputjuncname + ".in_intron.anchor" + ".canon",
	    cur_out_dir + outputjuncname + ".in_intron.anchor" + ".noncanon",
	    cur_out_dir + outputjuncname + ".exceed_intron.anchor" + ".canon",
	    cur_out_dir + outputjuncname + ".exceed_intron.anchor" + ".noncanon")
	    
def print_arguments(argu_file):
    
    
    print >> sys.stderr, "print argugment"
    
    argu_log = open(argu_file, "w")
    
    print >> argu_log, "min_anchor_length=[%s]" % (min_anchor_length)
    
    print >> argu_log, "seed_length=[%s]" % (seed_length)

    print >> argu_log, "splice_mismatches=[%s]" % (splice_mismatches)

    print >> argu_log, "segment_mismatches=[%s]" % (segment_mismatches)

    print >> argu_log, "FASTA_file_extension=[%s]" % (segment_mismatches)

    print >> argu_log, "read_file_suffix=[%s]" % (read_file_suffix)

    print >> argu_log, "min_intron_length=[%s]" % (min_intron_length)

    print >> argu_log, "max_intron_length=[%s]" % (max_intron_length)

    print >> argu_log, "island_extension=[%s]" % (max_intron_length)
    
    print >> argu_log, "read_width=[%s]" % (read_width)

    print >> argu_log, "rank=[%s]" % (rank)

    print >> argu_log, "flank_case=[%s]" % (flank_case)

    print >> argu_log, "fusion_flank_case=[%s]" % (fusion_flank_case)

    print >> argu_log, "islands_file=[%s]" % (islands_file)

    print >> argu_log, "read_files_dir=[%s]" % (read_files_dir)

    print >> argu_log, "chromosome_files_dir=[%s]" % (chromosome_files_dir)
    
    print >> argu_log, "all_chromosomes_file=[%s]" % (all_chromosomes_file)

    print >> argu_log, "repeat_regioins=[%s]" % (repeat_regioins)
    
    print >> argu_log, "gene_regions=[%s]" % (gene_regions)
    
    print >> argu_log, "bwt_idx_prefix=[%s]" % (bwt_idx_prefix)
    
    print >> argu_log, "bowtie_threads=[%s]" % (bowtie_threads)
    
    print >> argu_log, "max_hits=[%s]" % (max_hits)
    
    print >> argu_log, "threshold=[%s]" % (threshold)
    
    print >> argu_log, "boundary=[%s]" % (boundary)

    print >> argu_log, "num_anchor=[%s]" % (num_anchor)
    
    print >> argu_log, "unmapped_reads=[%s]" % (unmapped_reads)

    print >> argu_log, "sam_formatted=[%s]" % (sam_formatted)

    print >> argu_log, "bam_file=[%s]" % (bam_file)
    
    print >> argu_log, "sam_formatted_25=[%s]" % (sam_formatted_25)
 
    print >> argu_log, "bwt_map_25=[%s]" % (bwt_map_25)
    
    print >> argu_log, "pileup_file=[%s]" % (pileup_file)
    
    print >> argu_log, "synthetic_mappedreads=[%s]" % (synthetic_mappedreads)
    
    print >> argu_log, "tophat_mappedreads=[%s]" % (tophat_mappedreads)
    
    print >> argu_log, "pairend=[%s]" % (pairend)
    
    print >> argu_log, "gamma=[%s]" % (gamma)
    
    print >> argu_log, "delta=[%s]" % (delta)
    
    #print >> argu_log, "num_seg=[%s]" % (num_seg)

    print >> argu_log, "seg_len=[%s]" % (seg_len)

    print >> argu_log, "fix_hole_file=[%s]" % (fix_hole_file)
    
    print >> argu_log, "format_flag=[%s]" % (format_flag)
    
    print >> argu_log, "chrom_size_file=[%s]" % (chrom_size_file)
    
    print >> argu_log, "extend_bits=[%s]" % (extend_bits)
    
    print >> argu_log, "total_fusion_mismatch=[%s]" % (total_fusion_mismatch)
    
    print >> argu_log, "total_mismatch=[%s]" % (total_mismatch)
    
    print >> argu_log, "append_mismatch=[%s]" % (append_mismatch)
    
    print >> argu_log, "remap_mismatch=[%s]" % (remap_mismatch)
    
    print >> argu_log, "skip_bwt=[%s]" % (skip_bwt)
    
    print >> argu_log, "prefix_match=[%s]" % (prefix_match)
    
    print >> argu_log, "fullrunning=[%s]" % (fullrunning)
    
    print >> argu_log, "collect_stat=[%s]" % (collect_stat)
    
    print >> argu_log, "rm_temp=[%s]" % (rm_temp)
    
    print >> argu_log, "format_reads=[%s]" % (format_reads)
    
    print >> argu_log, "format_chromos=[%s]" % (format_chromos)
    
    print >> argu_log, "do_fusion=[%s]" % (do_fusion)
    
    print >> argu_log, "do_cluster=[%s]" % (do_cluster)
    
    print >> argu_log, "search_whole_chromo=[%s]" % (search_whole_chromo)
    
    print >> argu_log, "map_segment_directly=[%s]" % (map_segment_directly)
    
    print >> argu_log, "run_mapper=[%s]" % (run_mapper)
    
    print >> argu_log, "max_insert=[%s]" % (max_insert)
    
    print >> argu_log, "min_missed_seg=[%s]" % (min_missed_seg)
    
    print >> argu_log, "do_annot_gene=[%s]" % (do_annot_gene)
    
    print >> argu_log, "do_annot_gene=[%s]" % (annot_gene_file)
    
    print >> argu_log, "do_filter_fusion_by_repeat=[%s]" % (do_filter_fusion_by_repeat)
    
def main(argv=None):
   
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hv:o:s:n:m:i:x:w:S:R:B:p:t:u:c:f:a:d:g:T:D:U:M:P:N:X:G:L:H:E:Y:I:Q:A:F:C:e:K:r:O:", 
                                        ["version",
                                         "help",  
                                         "seed-length=",
                                         "splice-mismatches=",
					 "segment-mismatches=",
					 "read-file-suffix=",
                                         "min-anchor-length=",
                                         "min-intron-length=",
                                         "max-intron-length=",
                                         "extend-exons=",
                                         "read-width=", 
                                         "non-canonical",
					 "semi-canonical",
                                         "fusion-non-canonical",
					 "fusion-semi-canonical",
                                         "delta=",
                                         "gamma=",
                                         "threshold=",
                                         "boundary=",
                                         "Rank=",
                                         "Bowtieidx=",
					 "threads=",
                                         "islands-file=",
                                         "reads-file=",
                                         "chromosome-files-dir=",
                                         "all-chromosomes-files=",
                                         "FASTA-files=",
                                         "unmapped-reads=",
                                         "sam-file=",
					 "full-running",
					 "num-anchor=",
                                         "pileup-file=",
					 "numseg=",
					 "seglen=",
					 "fixholefile=",
					 "synthetic=",
					 "tophat=",
					 "pairend",
					 "fastq=",
					 "extend-bits=",
					 "total-mismatch=",
					 "total-fusion-mismatch=",
                                         "output-dir=",
					 "chrom-size=",
					 "skip-bowtie=",
					 "prefix-match=",
					 "collect-stat",
					 "max-hits=",
					 "not-rem-temp",
					 "not-rerun-all",
					 "format-chromos",
					 "format-reads",
					 "fusion",
					 "cluster",
					 "DEBUG",
					 "run-MapPER",
					 "search-whole-chromosome",
					 "map-segments-directly",
					 "remap-mismatches=",
					 "avoid-regions=",
					 "config=",
					 "interested-regions=",
					 "max-insert=",
	                                 "bam=",
					 "min-missed-seg=",
	                                 "annotgene=",
	                                 "filter-fusion-by-repeat=",
					 "append-mismatch="])
        except getopt.error, msg:
            raise Usage(msg)
        
        min_anchor_length = 8
	seed_length = 10
        splice_mismatches = 1
	segment_mismatches = 1
	FASTA_file_extension = "fa"
	read_file_suffix = "txt"
        min_intron_length = 10
        max_intron_length = 200000
        island_extension = 0
        read_width = 0
        rank = 0.0
        flank_case = 5
        fusion_flank_case = 5
        islands_file = ""
        read_files_dir = ""
        chromosome_files_dir = ""
        all_chromosomes_file = ""
	repeat_regioins = ""
	gene_regions = ""
        
        bwt_idx_prefix = ""
        bowtie_threads = 1
	max_hits = 4
        threshold = 1
        boundary = 50

        num_anchor = 1
        
        unmapped_reads = ""
        sam_formatted = ""
	bam_file = ""
	
        sam_formatted_25 = ""
	bwt_map_25 = ""
	
        pileup_file = ""
	
	synthetic_mappedreads = ""
	
	tophat_mappedreads = ""
	
	pairend = ""
        
        gamma = 0.1
        delta = 0.1
	
	num_seg = 4
	
	seg_len = 25

	fix_hole_file = "" 
	
	format_flag = ""
	
	chrom_size_file = ""
	
	extend_bits = 3
	
	total_fusion_mismatch = 2
	
	total_mismatch = 2
	
	append_mismatch = 2
	
	remap_mismatch = 2
	
	skip_bwt = 0
	
	prefix_match = 1
	
	fullrunning = 0
	
	collect_stat = 0
	
	rm_temp = 1
	
	format_reads = 0
	
	format_chromos = 0
	
	do_fusion = 0
	
	do_cluster = 0
	
	search_whole_chromo = 0
	
	map_segment_directly = 0
	
	run_mapper = 0
	
	max_insert = 3
	
	min_missed_seg = 0
	
	do_annot_gene = 0
	
	annot_gene_file = ""
	
	do_filter_fusion_by_repeat = 0
	
	chrom_blat = ""
	
	junction_tobe_syn = ""
	
	global rerun_all
	
	global DEBUG
	
	if len(args) == 1:
	    params = Params()
	    
	    params.parse_cfgfile(args[0])
	    
	    min_anchor_length = params.min_anchor_length
	    seed_length = params.seed_length
	    splice_mismatches = params.splice_mismatches
	    segment_mismatches = params.segment_mismatches
	    FASTA_file_extension = params.FASTA_file_extension
	    read_file_suffix = params.read_file_suffix
	    min_intron_length = params.min_intron_length
	    max_intron_length = params.max_intron_length
	    island_extension = params.island_extension
	    read_width = params.read_width
	    rank = params.rank
	    flank_case = params.flank_case
	    fusion_flank_case = params.fusion_flank_case
	    islands_file = params.islands_file
	    read_files_dir = params.read_files_dir
	    chromosome_files_dir = params.chromosome_files_dir
	    all_chromosomes_file = params.all_chromosomes_file
	    repeat_regioins = params.repeat_regioins
	    gene_regions = params.gene_regions	    
	    bwt_idx_prefix = params.bwt_idx_prefix
	    bowtie_threads = params.bowtie_threads
	    max_hits = params.max_hits
	    threshold = params.threshold
	    boundary = params.boundary    
	    num_anchor = params.num_anchor	    
	    unmapped_reads = params.unmapped_reads
	    sam_formatted = params.sam_formatted
	    sam_formatted_25 = params.sam_formatted_25
	    bwt_map_25 = params.bwt_map_25	    
	    pileup_file = params.pileup_file	    
	    synthetic_mappedreads = params.synthetic_mappedreads
	    tophat_mappedreads = params.tophat_mappedreads	    
	    pairend = params.pairend	    
	    gamma = params.gamma
	    delta = params.delta	    
	    #num_seg = params.num_seg
	    seg_len = params.seg_len    
	    fix_hole_file = params.fix_hole_file	    
	    format_flag = params.format_flag	    
	    chrom_size_file = params.chrom_size_file	    
	    extend_bits = params.extend_bits	    
	    total_fusion_mismatch = params.total_fusion_mismatch	    
	    total_mismatch = params.total_mismatch	    
	    append_mismatch = params.append_mismatch	    
	    remap_mismatch = params.remap_mismatch	    
	    skip_bwt = params.skip_bwt	    
	    prefix_match = params.prefix_match	    
	    fullrunning = params.fullrunning	    
	    collect_stat = params.collect_stat	    
	    rm_temp = params.rm_temp	    
	    format_reads = params.format_reads	    
	    format_chromos = params.format_chromos	    
	    do_fusion = params.do_fusion	    
	    do_cluster = params.do_cluster	    
	    search_whole_chromo = params.search_whole_chromo	    
	    map_segment_directly = params.map_segment_directly	    
	    run_mapper = params.run_mapper
	    max_insert = params.max_insert
	    bam_file = params.bam_file
	    min_missed_seg = params.min_missed_seg
	    do_annot_gene = params.do_annot_gene
	    annot_gene_file = params.annot_gene_file
	    do_filter_fusion_by_repeat = params.filter_fusion_by_repeat
	    chrom_blat = params.chromosome_blat_idx
                              
        # option processing
        for option, value in opts:
            value = value.strip()
            if option in ("-o", "--output-dir"):
                global output_dir
                global logging_dir
		global canon_in_intron_dir
		global canon_exceed_intron_dir
		global noncanon_in_intron_dir
		global noncanon_exceed_intron_dir
		global fusion_dir
		global temp_dir
		global synthetic_dir
		global pairend_dir
		global original_dir
		global filteredbest_dir
		global comparison_dir
		global tophat_dir
		global remap_dir
		global remap_regions_dir
		global hmer_dir
		global hole_dir
		global head_dir
		global tail_dir
		global bwtout_dir
		global sam_dir
		global formated_chrom_dir
		global formated_reads_dir
		global fusion_dir
		global fusion_data_dir
		global fusion_data_single_dir
		global fusion_data_PER_dir
		global fusion_result_dir
		global fusion_result_PER_prob_dir
		global fusion_result_junction_support_dir
		global cluster_dir
		global cluster_result_dir
		global cluster_data_dir
		global cluster_data_parsedPER_dir
		global fusion_result_fusionRead_dir
               
                output_dir = value + "/"
                logging_dir = output_dir + "logs/"
		canon_in_intron_dir = output_dir + "canonical/"
		canon_exceed_intron_dir = output_dir + "canonical_exceed/"
		noncanon_in_intron_dir = output_dir + "noncanonical/"
		noncanon_exceed_intron_dir = output_dir + "noncanonical_exceed/"
		fusion_dir = output_dir + "fusion/"
		temp_dir = output_dir + "tmp/"
		
		synthetic_dir = temp_dir + "synthetic/"
		
		pairend_dir = temp_dir + "pairend/"
		
		original_dir = temp_dir + "original/"
		filteredbest_dir = temp_dir + "best/"
		comparison_dir = temp_dir + "comparison/"
		
		tophat_dir = temp_dir + "tophat/"
		
		remap_dir = temp_dir + "remap/"
		
		remap_regions_dir = temp_dir + "remap_regions/"
		
		hmer_dir = temp_dir + "single_anchored_middle/"
		hole_dir = temp_dir + "double_anchored/"
		head_dir = temp_dir + "single_anchored_head/"
		tail_dir = temp_dir + "single_anchored_tail/"
		bwtout_dir = temp_dir + "bwtout/"
		
		sam_dir = temp_dir + "sam/"
		
		fusion_dir = temp_dir + "fusion/"
		
		cluster_dir = temp_dir + "cluster/"
		
		cluster_result_dir = cluster_dir + "result/"
		cluster_data_dir = cluster_dir + "data/"
		cluster_data_parsedPER_dir = cluster_data_dir + "parsedPER/"
		
		fusion_data_dir = fusion_dir + "data/"
		fusion_data_single_dir = fusion_data_dir + "single/"
		fusion_data_PER_dir = fusion_data_dir + "PER/"
		fusion_result_dir = fusion_dir + "result/"
		fusion_result_PER_prob_dir = fusion_result_dir + "PER_prob/"
		fusion_result_junction_support_dir = fusion_result_dir + "junction_support/"
		fusion_result_fusionRead_dir = fusion_result_dir + "fusionRead/"
				
		formated_chrom_dir = temp_dir + "formated_chrom/"

		formated_reads_dir = temp_dir + "formated_reads/"
		
		 
		
            if option in ("-v", "--version"):
                print "MapSplice v%s" % (get_version())
                exit(0)
            if option in ("-h", "--help"):
                raise Usage(use_message)
            if option in ("-f", "--config"):
                a = 0
            if option in ("-w", "--read-width"):
                read_width = int(value)
                if not read_width >= 1:
                    print >> sys.stderr, "Error: arg to --read-width must be greater than or equal to 1"
                    exit(1)
            if option in ("-n", "--min-anchor"):
                min_anchor_length = int(value)
                if min_anchor_length < 4:
                    print >> sys.stderr, "Error: arg to --min-anchor-len must be greater than 3"
                    exit(1)
            if option in ("-N", "--num-anchor"):
                num_anchor = int(value)
                if num_anchor <= 0:
                    print >> sys.stderr, "Error: arg to --num-anchor must be greater than 0"
                    exit(1)
	    if option in ("-r", "--max-insert"):
                max_insert = int(value)
                if max_insert <= 0:
                    print >> sys.stderr, "Error: arg to --max-insert must be greater than 0"
                    exit(1)
	    if option in ("-K", "--append-mismatch"):
                append_mismatch = int(value)
                if append_mismatch < 0:
                    print >> sys.stderr, "Error: arg to --num-anchor must be greater or equal to 0"
                    exit(1)
            if option in ("-s", "--read-file-suffix"):
                read_file_suffix = value
            if option in ("-m", "--splice-mismatches"):
                splice_mismatches = int(value)
                if not splice_mismatches >= 0:
                    print >> sys.stderr, "Error: arg to --splice-mismatches must be greater than or equal to 0"
                    exit(1)
	    if option in ("-e", "--extend-bits"):
                extend_bits = int(value)
                if not extend_bits >= 0:
                    print >> sys.stderr, "Error: arg to --extend-bits must be greater than or equal to 0"
                    exit(1)
	    if option in ("-C", "--total-mismatch"):
                total_mismatch = int(value)
                if not total_mismatch >= 0:
                    print >> sys.stderr, "Error: arg to --total-mismatch must be greater than or equal to 0"
                    exit(1)
	    if option in ("-F", "--total-fusion-mismatch"):
                total_fusion_mismatch = int(value)
                if not total_fusion_mismatch >= 0:
                    print >> sys.stderr, "Error: arg to --total-fusion-mismatch must be greater than or equal to 0"
                    exit(1)
	    if option in ("-E", "--segment-mismatches"):
                segment_mismatches = int(value)
                if not segment_mismatches >= 0:
                    print >> sys.stderr, "Error: arg to --segment-mismatches must be greater than or equal to 0"
                    exit(1)
            if option in ("-i", "--min-intron-length"):
                min_intron_length = int(value)
                if min_intron_length <= 0:
                    print >> sys.stderr, "Error: arg to --min-intron-length must be greater than 0"
                    exit(1)                
            if option in ("-x", "--max-intron-length"):
                max_intron_length = int(value)
                if max_intron_length <= 0:
                    print >> sys.stderr, "Error: arg to --max-intron-length must be greater than 0"
                    exit(1)
	    if option in ("-X", "--threads"):
                bowtie_threads = int(value)
                if bowtie_threads <= 0:
                    print >> sys.stderr, "Error: arg to --threads must be greater than 0"
                    exit(1)
            if option in ("-T", "--interested-regions"):
                gene_regions = value
	    #if option in ("-G", "--numseg"):
                #num_seg = int(value)
		#
	    if option in ("-L", "--seglen"):
                seg_len = int(value)
	    if option in ("-O"):
                junction_tobe_syn = value
		#
	    if option in ("-H", "--fixholefile"):
                fix_hole_file = value
		#
	    
            if option in ("-D", "--boundary"):
                boundary = int(value)
                if boundary <= 0:
                    print >> sys.stderr, "Error: arg to --boundary must be greater than 0"
                    exit(1)
		
            if option in ("-p", "--extend-exons"):
                island_extension = int(value)
                if island_extension < 0:
                    print >> sys.stderr, "Error: arg to --extend-exons must be at least 0"
                    exit(1)
            if option == "--non-canonical":
                flank_case = 0
	    if option == "--semi-canonical":
		flank_case = 1
            if option == "--fusion-non-canonical":
                fusion_flank_case = 0
	    if option == "--fusion-semi-canonical":
		fusion_flank_case = 1
            if option in ("-R", "--remap-mismatches"):
                remap_mismatch =int(value)
                if remap_mismatch < 0 or remap_mismatch > 3:
                    print >> sys.stderr, "Error: arg to --remap-mismatch must be in [0, 3]"
                    exit(1)
	    
            #if option in ("-d", "--delta"):
                #delta =float(value)
                #if delta < 0.0000001:
                    #print >> sys.stderr, "Error: arg to --delta must be at least 0.0000001"
                    #exit(1)
            #if option in ("-g", "--gamma"):
                #gamma =float(value)
                #if gamma < 0.0000001:
                    #print >> sys.stderr, "Error: arg to --gamma must be at least 0.0000001"
                    #exit(1)
            if option in ("-S", "--FASTA-files-ext"):
                FASTA_file_extension = value
            if option in ("-a", "--all-chromosomes-files"):
                all_chromosomes_file = value
            if option in ("-B", "--Bowtieidx"):
                bwt_idx_prefix = value
            if option in ("-u", "--reads-file"):
                read_files_dir = value
	    if option in ("-t", "--avoid-regions"):
                repeat_regioins = value
            if option in ("-U", "--unmapped-reads"):
                unmapped_reads = value
            if option in ("-M", "--sam-file"):
                sam_formatted = value
            if option in ("-P", "--pileup-file"):
                pileup_file = value
	    if option in ("-Y", "--synthetic"):
                synthetic_mappedreads = value
	    if option in ("-A", "--tophat"):
                tophat_mappedreads = value
	    if option in ("-Q", "--reads-format"):
		if value.strip() == "fq":
		    format_flag = "-q"
		elif value.strip() == "fa":
		    format_flag = "-f"
	    if option in ("-g","--skip-bowtie"):
		skip_bwt = int(value)
	    if option in ("-d","--prefix-match"):
		prefix_match = int(value)
            if option in ("-c", "--chromosome-files-dir"):
                chromosome_files_dir = value
		chromosome_files_dir = chromosome_files_dir + "/"
	    if option == "--collect-stat":
                collect_stat = 1
	    if option == "--chrom-size":
                chrom_size_file = value
	    if option == "--bam":
                bam_file = value 
	    if option == "--full-running":
                fullrunning = 1
		if fullrunning < 0:
                    print >> sys.stderr, "Error: arg to --full-running must be greater than or equal to 0"
                    exit(1)    	    		    
	    if option == "--max-hits":
		max_hits = int(value)
	    if option == "--min-missed-seg":
		min_missed_seg = int(value)
	    if option == "--not-rem-temp":
		rm_temp = 0
	    if option == "--not-rerun-all":
		rerun_all = 0
	    if option == "--format-chromos":
		format_chromos = 1
	    if option == "--cluster":
		do_cluster = 1
	    if option == "--fusion":
		do_fusion = 1
	    if option == "--search-whole-chromosome":
		search_whole_chromo = 1
	    if option == "--map-segments-directly":
		map_segment_directly = 1
	    if option == "--run-MapPER":
		run_mapper = 1
	    if option == "--DEBUG":
		DEBUG = 1
	    if option == ("--pairend"):
                pairend = "1"
	    if option == ("--annotgene"):
		do_annot_gene = 1
		annot_gene_file = value
	    if option == ("--filter-fusion-by-repeat"):
		do_filter_fusion_by_repeat = 1
		chrom_blat = value
		#print >> sys.stderr, "chrom_blat=[%s]" % (chrom_blat)

	start_time = datetime.now()
	
        prepare_output_dir()
	
	#print_arguments("argu_log")
	print_argu = 1
	if print_argu > 0:
	    #print >> sys.stderr, "print argugment"
	
	    argu_file = logging_dir + "argu_log"
	    
	    argu_log = open(argu_file, "w")
	    
	    
	    print >> argu_log, "output_dir=[%s]" % (output_dir)
	    
	    print >> argu_log, "min_anchor_length=[%s]" % (min_anchor_length)
	    
	    print >> argu_log, "seed_length=[%s]" % (seed_length)
	
	    print >> argu_log, "splice_mismatches=[%s]" % (splice_mismatches)
	
	    print >> argu_log, "segment_mismatches=[%s]" % (segment_mismatches)
	
	    print >> argu_log, "FASTA_file_extension=[%s]" % (FASTA_file_extension)
	
	    print >> argu_log, "read_file_suffix=[%s]" % (read_file_suffix)
	
	    print >> argu_log, "min_intron_length=[%s]" % (min_intron_length)
	
	    print >> argu_log, "max_intron_length=[%s]" % (max_intron_length)
	
	    print >> argu_log, "island_extension=[%s]" % (island_extension)
	    
	    print >> argu_log, "read_width=[%s]" % (read_width)
	
	    print >> argu_log, "rank=[%s]" % (rank)
	
	    print >> argu_log, "flank_case=[%s]" % (flank_case)
	
	    print >> argu_log, "fusion_flank_case=[%s]" % (fusion_flank_case)
	
	    print >> argu_log, "islands_file=[%s]" % (islands_file)
	
	    print >> argu_log, "read_files_dir=[%s]" % (read_files_dir)
	
	    print >> argu_log, "chromosome_files_dir=[%s]" % (chromosome_files_dir)
	    
	    print >> argu_log, "all_chromosomes_file=[%s]" % (all_chromosomes_file)
	
	    print >> argu_log, "repeat_regioins=[%s]" % (repeat_regioins)
	    
	    print >> argu_log, "gene_regions=[%s]" % (gene_regions)
	    
	    print >> argu_log, "bwt_idx_prefix=[%s]" % (bwt_idx_prefix)
	    
	    print >> argu_log, "bowtie_threads=[%s]" % (bowtie_threads)
	    
	    print >> argu_log, "max_hits=[%s]" % (max_hits)
	    
	    print >> argu_log, "threshold=[%s]" % (threshold)
	    
	    print >> argu_log, "boundary=[%s]" % (boundary)
	
	    print >> argu_log, "num_anchor=[%s]" % (num_anchor)
	    
	    print >> argu_log, "unmapped_reads=[%s]" % (unmapped_reads)
	
	    print >> argu_log, "sam_formatted=[%s]" % (sam_formatted)
	
	    print >> argu_log, "bam_file=[%s]" % (bam_file)
	    
	    print >> argu_log, "sam_formatted_25=[%s]" % (sam_formatted_25)
	 
	    print >> argu_log, "bwt_map_25=[%s]" % (bwt_map_25)
	    
	    print >> argu_log, "pileup_file=[%s]" % (pileup_file)
	    
	    print >> argu_log, "synthetic_mappedreads=[%s]" % (synthetic_mappedreads)
	    
	    print >> argu_log, "tophat_mappedreads=[%s]" % (tophat_mappedreads)
	    
	    print >> argu_log, "pairend=[%s]" % (pairend)
	    
	    print >> argu_log, "gamma=[%s]" % (gamma)
	    
	    print >> argu_log, "delta=[%s]" % (delta)
	    
	    #print >> argu_log, "num_seg=[%s]" % (num_seg)
	
	    print >> argu_log, "seg_len=[%s]" % (seg_len)
	
	    print >> argu_log, "fix_hole_file=[%s]" % (fix_hole_file)
	    
	    print >> argu_log, "format_flag=[%s]" % (format_flag)
	    
	    print >> argu_log, "chrom_size_file=[%s]" % (chrom_size_file)
	    
	    print >> argu_log, "extend_bits=[%s]" % (extend_bits)
	    
	    print >> argu_log, "total_fusion_mismatch=[%s]" % (total_fusion_mismatch)
	    
	    print >> argu_log, "total_mismatch=[%s]" % (total_mismatch)
	    
	    print >> argu_log, "append_mismatch=[%s]" % (append_mismatch)
	    
	    print >> argu_log, "remap_mismatch=[%s]" % (remap_mismatch)
	    
	    print >> argu_log, "skip_bwt=[%s]" % (skip_bwt)
	    
	    print >> argu_log, "prefix_match=[%s]" % (prefix_match)
	    
	    print >> argu_log, "fullrunning=[%s]" % (fullrunning)
	    
	    print >> argu_log, "collect_stat=[%s]" % (collect_stat)
	    
	    print >> argu_log, "rm_temp=[%s]" % (rm_temp)
	    
	    print >> argu_log, "format_reads=[%s]" % (format_reads)
	    
	    print >> argu_log, "format_chromos=[%s]" % (format_chromos)
	    
	    print >> argu_log, "do_fusion=[%s]" % (do_fusion)
	    
	    print >> argu_log, "do_cluster=[%s]" % (do_cluster)
	    
	    print >> argu_log, "search_whole_chromo=[%s]" % (search_whole_chromo)
	    
	    print >> argu_log, "map_segment_directly=[%s]" % (map_segment_directly)
	    
	    print >> argu_log, "run_mapper=[%s]" % (run_mapper)
	    
	    print >> argu_log, "max_insert=[%s]" % (max_insert)
	    
	    print >> argu_log, "min_missed_seg=[%s]" % (min_missed_seg)
	    
	    print >> argu_log, "do_annot_gene=[%s]" % (do_annot_gene)
	    
	    print >> argu_log, "do_annot_gene=[%s]" % (annot_gene_file)
	    
	    print >> argu_log, "do_filter_fusion_by_repeat=[%s]" % (do_filter_fusion_by_repeat)
	    
	    print >> argu_log, "do_filter_fusion_by_repeat=[%s]" % (chrom_blat)
	    
	    print >> argu_log, "junction_tobe_syn=[%s]" % (junction_tobe_syn)
	    
	    print >> argu_log, "rerun_all=[%s]" % (rerun_all)
	    
	    print >> argu_log, "DEBUG=[%s]" % (DEBUG)
	    
	    
		
	#if read_width == 0:
	    #print >> sys.stderr, "read width must be specified"
	    #exit(0)
	    
	if format_flag == "":
            format_flag = '-q'
	    #print >> sys.stderr, "read format must be specified"
	    #exit(0)
	    
	if bwt_idx_prefix == "":
	    print >> sys.stderr, "bowtie index must be specified"
	    exit(0)
	    
        print >> sys.stderr
        print >> sys.stderr, "[%s] Beginning Mapsplice run (v%s)" % (right_now(), get_version())
        print >> sys.stderr, "-----------------------------------------------" 

	global bin_dir
	
	print >> sys.stderr, "bin directory: [%s] " % bin_dir
	
	#num_seg = (int)(read_width / seg_len)
	
	#read_width = num_seg * seg_len
	
	#if min_missed_seg == 0:
	    #min_missed_seg = num_seg
	    
	min_seg = min_missed_seg
	#min_seg = math.ceil(1 * (float(num_seg)))
        
	write_current_stats("Beginning MapSplice run")
        # Validate all the input files, check all prereqs before committing 
        # to the run
        chromosome_files_dir = chromosome_files_dir.strip()
        format_chromos = check_chromo_files(chromosome_files_dir)
	
	if format_chromos > 0:
	    all_chromos_path = read_dir_by_suffix(chromosome_files_dir.strip(), FASTA_file_extension)
	
	    chromosome_files_dir = format_chromos_func(all_chromos_path)
	    
	    FASTA_file_extension = "fa"
	    
	sam_formatted_array = ""
	
	if bam_file != "":
	    bam_file_array = bam_file.split(',')	
	    for a_bam_file in bam_file_array:
		a_bam_file_name = a_bam_file.split('/')[-1]	
		sam_formatted = bam2sam(a_bam_file, temp_dir + a_bam_file_name + ".sam")
		sam_formatted_array = sam_formatted_array + sam_formatted + ","
		pairend = ""
	elif sam_formatted != "":
	    sam_formatted_array = sam_formatted
	    pairend = ""
	
	if pairend != "":
	    map_segment_directly = 1
		
	if sam_formatted != "":
	    read_files_dir = sam2fq(sam_formatted_array, temp_dir + "sam_reads.fq", "1", logging_dir + "sam2fq.log")
	    
	    format_flag = '-q'
	
	if format_reads > 0:
	    read_files_dir = format_reads_func(read_files_dir, formated_reads_dir + "formated_reads.txt")
        
        bwt_map = ""
	temp_unmapped_reads = ""
	BWT_sam = ""
	
	maxlen = 0
	
	max_seg = 0
	
        if unmapped_reads == "" or (pileup_file == ""):
	    chrom_dir_files = chromosome_files_dir
	    if all_chromosomes_file != "":
		chrom_dir_files = all_chromosomes_file
		
            check_bowtie_index(bwt_idx_prefix, chrom_dir_files, 0, FASTA_file_extension)
            
            #reads_files = read_sequence_by_suffix(read_files_dir, )
	    reads_files = read_sequence_by_suffix(read_files_dir, read_file_suffix)
            
	    repeat_fasta = temp_dir + "repeat_reads"
	    
	    if collect_stat > 1:
		countline(reads_files, logging_dir + "reads_files.log")
	    
	    temp_unmapped_reads = reads_files
	    
	    #--------------------merge paired end reads-----------------------#

	    #temp_unmapped_reads = merge_paired_end_reads(reads_files, format_flag, pairend, temp_dir + "merged_paired_reads")
	    
	    check_reads_format(reads_files, format_flag, pairend)
	    
	    temp_unmapped_reads = merge_paired_end_reads_rmshort(reads_files, format_flag, pairend, seg_len, temp_dir + "merged_paired_reads")
	    
	    maxlen = extract_maxlen(logging_dir + "merge_paired_end_reads_rmshort.log")	
	    
	    max_seg = (int)(maxlen / seg_len)
	    
	    bowtie_seed_length = maxlen - 2
	    
	    if splice_mismatches == 0:
		bowtie_seed_length = maxlen
		
	    #merge_paired_end_reads_rmshort(reads_files, format_flag, paired, read_len, merged_reads)
	    
	    #indexed_reads = index_reads(temp_unmapped_reads, format_flag, temp_dir + "indexed_reads")
	    
	    bwt_map = temp_dir + "unspliced_mapped_reads"	    
	    
	    bwt_map_handler = open(bwt_map, "w")
	    
  	    if junction_tobe_syn == "":
	    #-------------------bowtie whole reads mapping--------------------#
		if map_segment_directly == 0:
		    (bwt_map, temp_unmapped_reads) = bowtie(bwt_idx_prefix, 
			                               temp_unmapped_reads,
			                               format_flag, 
			                               "unspliced_mapped_reads",
			                               "unmappedreads",
			                               bowtie_threads,
			                               bowtie_seed_length,
			                               max_hits*10,
			                               repeat_fasta,
			                               segment_mismatches,
			                               logging_dir + "unspliced_reads.log")
		    if repeat_regioins != "":
			(bwt_map_inrepeat, bwt_map) = FilterBWTByRegions(bwt_map, repeat_regioins, bwt_map + ".in_repeat", bwt_map + ".notin_repeat", logging_dir + "filterbyregion_seg.log")
		    
		    if gene_regions != "":
			(bwt_map, bwt_map_notin_gene) = FilterBWTByRegions(bwt_map, gene_regions, bwt_map + ".in_gene", bwt_map + ".notin_gene", logging_dir + "filterbyregion_seg_gene.log")
		
		bowtie2sam(bwt_map, 0, temp_dir + "unspliced_mapped.sam", logging_dir + "bowtie2sam.log")
		
		BWT_sam = temp_dir + "unspliced_mapped.sam"
	    
	    #elif skip_bwt == 1:
		#open(temp_dir + "unspliced_map.bwtout", "w")
		#bwt_map = temp_dir + "unspliced_map.bwtout"
		#temp_unmapped_reads = reads_files
	
	if unmapped_reads == "":
	    unmapped_reads = temp_unmapped_reads
	
	#------------------divide reads into segments---------------#
	
	divided_reads = ""
	
	if junction_tobe_syn == "":
	    if bowtie_threads > 1 and map_segment_directly == 0:
		divided_reads = dividereadsindexed(unmapped_reads, seg_len, format_flag)
	    else:
		divided_reads = dividereads(unmapped_reads, seg_len, format_flag)
    
	    repeat_fasta_25bp = temp_dir + "repeat_segments"
	
	bowtie_seg_seed_length = seg_len - 5
	
	if segment_mismatches == 0:
	    bowtie_seg_seed_length = seg_len
	    
	#------------------bowtie segments mapping-------------------#
	 
	write_current_stats("Aligning segments")
	
	if junction_tobe_syn == "":
	    (bwt_map_25, temp_unmapped_reads_25) = bowtie(bwt_idx_prefix, 
		                                   divided_reads,
		                                   format_flag, 
		                                   "unspliced_mapped_segments",
		                                   "unmapped_segments",
		                                   bowtie_threads,
		                                   bowtie_seg_seed_length,
		                                   max_hits * 10,
		                                   repeat_fasta_25bp,
		                                   segment_mismatches,
		                                   logging_dir + "unspliced_segments.log")
    
	    if repeat_regioins != "":
		(bwt_map_25_inrepeat, bwt_map_25) = FilterBWTByRegions(bwt_map_25, repeat_regioins, bwt_map_25 + ".in_repeat", bwt_map_25 + ".notin_repeat", logging_dir + "filterbyregion_reads.log")
	    
	    if gene_regions != "":
		(bwt_map_25, bwt_map_25_notin_gene) = FilterBWTByRegions(bwt_map_25, gene_regions, bwt_map_25 + ".in_gene", bwt_map_25 + ".notin_gene", logging_dir + "filterbyregion_reads_gene.log")

	bwt_map_25_sorted = bwt_map_25
	
	if junction_tobe_syn == "":
	    if bowtie_threads > 1:
		bwt_map_25_sorted = sort_segment_bwt(bwt_map_25, bwt_map_25 + ".sorted")
	    
	    divided_reads_oneline_sorted = divided_reads
	
	    all_chromos_path = read_dir_by_suffix(chromosome_files_dir, FASTA_file_extension)
	    
	    chromo_size_file = read_chromo_sizes(all_chromos_path, temp_dir + "chrom_sizes", fusion_dir + "chrName.txt")
	
	    #----------------------candidate generation------------------#
	    
	    
	    islands_file = mapsplice_search(1, max_intron_length, seg_len, extend_bits, divided_reads_oneline_sorted, format_flag, chromo_size_file, 
		         bwt_map, 45, boundary, temp_dir + "islands.gff", bwt_map_25_sorted, pairend, max_insert)

	Fqunmapped = ""
	
	if format_flag == "-q":
	    Fqunmapped = unmapped_reads

	#----------------------fill missing segment------------------#
	
	#if gene_regions != "":
	    #islands_file = gene_regions
	
	write_current_stats("Aligning spliced reads")
	
	if junction_tobe_syn == "":
	    juncs_file = call_mapsplice_segment(islands_file, 
		                        seed_length,
		                        maxlen,
		                        min_anchor_length,
		                        splice_mismatches,
		                        1,
		                        max_intron_length,
		                        island_extension,
		                        flank_case,
		                        0.0,
		                        FASTA_file_extension,
		                        divided_reads,
		                        chromosome_files_dir,
		                        num_anchor,
		                        num_seg,
		                        seg_len,
		                        bwt_map_25,
		                        fix_hole_file,
		                        output_dir,
		                        Fqunmapped,
		                        extend_bits,
		                        total_mismatch,
		                        total_fusion_mismatch,
		                        append_mismatch,
		                        prefix_match,
		                        2,
		                        search_whole_chromo,
		                        max_insert)	

	ori_single_sam = original_dir + "original_spliced.sam"
	
	original_spliced_sam_sorted = ori_single_sam
	
	ori_paired_sam = ""
	
	#if pairend != "":
	    
	    #ori_single_sam = original_dir + "ori_single.sam"
	    
	    #ori_paired_sam = original_dir + "ori_paired.sam"	    
	    
	    #original_spliced_sam_sorted = original_dir + "ori_single.sam"
	
	#min_seg = math.ceil(0.75 * (float(num_seg)))
	
	#----------------------assemble mapped segments------------------#
	
	if junction_tobe_syn == "":
	    original_spliced_sam = mapsplice_report(seg_len, chromo_size_file, extend_bits, divided_reads_oneline_sorted, 
		                                    format_flag, bwt_map_25_sorted, max_intron_length, temp_dir + "fusion_tobefixed.txt", 
		                                    ori_single_sam, ori_paired_sam, min_seg, min_seg - 1, do_fusion, pairend)
	
	    original_spliced_sams = [original_spliced_sam]
	
	#if (pairend != ""):
	    #original_spliced_sams = original_spliced_sams + [ori_paired_sam] + [ori_paired_sam + ".filtered"]
	    
	    #original_spliced_sams = merge_chromo_sams(original_spliced_sams, original_dir + "original_spliced_merged.sam", logging_dir + "original_fusion.log")
	    
	    #original_spliced_sam_sorted = sort_segment_bwt1(original_spliced_sams, 
						#original_dir + "original_spliced_merged_sorted.sam")
	
	if junction_tobe_syn == "":					
	    if bowtie_threads > 1 and map_segment_directly == 0:
		original_spliced_sams = remove_index_sam(original_spliced_sam_sorted, original_dir + "original_spliced_merged_sorted_rmidx.sam")
		
		original_spliced_sam_sorted = sort_segment_bwt1(original_dir + "original_spliced_merged_sorted_rmidx.sam", 
		                                    original_dir + "original_spliced_merged_sorted_rmidx_sorted.sam")

	##if pairend != "":

	    #####fusion_paired_sam = ""
	    
	    #####real_single_sam = ""
	    
	    #####cluster(fusion_paired_sam, region_file, log_file)
		
	    #####ReadRegions(region_file, real_single_sam, reads_file, out_path, format_flag, chrom_dir, output_dir_file, log_file)
	    
	    #####arguments = ""
	    
	    #####generate_bash_file_and_run(output_dir_file, bash_file, abs_path, arguments, log_file)
	    
	    #####convert_to_abs_offset(output_dir_file, sam_output_file, fusion_output_file, abs_path, log_file)
	    
	    #####-----------------remove duplication of paired reads----------------------#
	    ####RemDup(original_dir + "ori_paired.sam", original_dir + "ori_paired.unique.sam", 
	       ####original_dir + "ori_paired.multiple.sam", logging_dir + "ori_paired.stat", logging_dir + "ori_paired.log")
	    
	    ##sam2juncarray([original_dir + "ori_paired.sam",], original_dir + "ori.paired.junc.txt", 
		      ##chromosome_files_dir, read_width, 1, 350000000, "", 1, logging_dir + "ori.paired.junc.log")
	    
	    ##sam2juncarray([original_dir + "ori_single.sam",], original_dir + "ori.single.junc.txt", 
		      ##chromosome_files_dir, read_width, 1, 350000000, "", 1, logging_dir + "ori.single.junc.log")
	
	if junction_tobe_syn == "":
	    if do_fusion >= 1 and (fullrunning == 0 or pairend == '' or do_cluster == 0):
		
		#-----------------fill missed segment for fusion------------------------#
		juncs_file = call_mapsplice_segment_fusion(islands_file, 
		                            seed_length,
		                            maxlen,
		                            min_anchor_length,
		                            splice_mismatches,
		                            1,
		                            max_intron_length,
		                            island_extension,
		                            fusion_flank_case,
		                            0.0,
		                            FASTA_file_extension,
		                            divided_reads,
		                            chromosome_files_dir,
		                            num_anchor,
		                            num_seg,
		                            seg_len,
		                            bwt_map_25,
		                            fix_hole_file,
		                            output_dir,
		                            Fqunmapped,
		                            extend_bits,
		                            total_mismatch,
		                            total_fusion_mismatch,
		                            append_mismatch,
		                            prefix_match,
		                            2,
		                            fusion_dir + "original_fusion_junction")
		
		fusion_fixed = read_dir_by_suffix(fusion_dir, "fixed")
		
		original_fusion_sam = merge_chromo_sams(fusion_fixed, fusion_dir + "original_fusion.sam", logging_dir + "original_fusion.log")
		
		#original_fusion_sam_sorted = sort_segment_bwt1(fusion_dir + "original_fusion.sam", fusion_dir + "original_fusion.sam.sorted")
		
		#----------------filter multiple mapping fusion reads----------------------#
		 
		#separatedmultipleuniquefusion(fusion_dir + "original_fusion.sam.sorted", output_dir + "fusion.mapped.unique", 
					      #fusion_dir + "original_fusion.sam.sorted.multiple", logging_dir + "fusion.stat")
	    
		#----------------convert to fusion junction----------------------#
		#fusionsam2junc1(output_dir + "fusion.mapped.unique", fusion_dir + "fusion_junction.unique", read_width, "", 
				#logging_dir + "fusionsam2junc_unique.log")
    
		fusionsam2junc1(fusion_dir + "original_fusion.sam", output_dir + "fusion.junction", maxlen, "", 
		                logging_dir + "fusionsam2junc_unique.log")
	    
		#filterfusionjuncbyminmis(fusion_dir + "fusion_junction.unique", 1, output_dir + "fusion.junction",
					 #fusion_dir + "fusion.unique.junction.not_in_min_mis", logging_dir + "filter_fusion_by_minmis.log")
	
	if junction_tobe_syn == "":				 
	    sam2juncarray([original_spliced_sam_sorted], original_dir + "ori.all_junctions.txt", chromosome_files_dir, 
		 maxlen, 1, 350000000, "", 1, logging_dir + "sam2junc_ori.all_junctions.log")
	    
	BWT_sam = temp_dir + "unspliced_mapped.sam"
	
	if junction_tobe_syn == "":
	    if map_segment_directly == 0:
		
		bwt_map_sorted = temp_dir + "unspliced_mapped.sam"
		
		if bowtie_threads > 1:
		    bwt_map_sorted = sort_by_name1(temp_dir + "unspliced_mapped.sam", temp_dir + "unspliced_mapped_sorted.sam")
		
		RemDup(bwt_map_sorted, temp_dir + "unspliced_mapped_sorted.unique.sam", 
		       temp_dir + "unspliced_mapped_sorted.multiple.sam", logging_dir + "unspliced_mapped_sorted.stat", 
		       logging_dir + "unspliced_mapped_sorted.log")
		
		FilterMultipleMapped(temp_dir + "unspliced_mapped_sorted.multiple.sam", original_dir + "ori.all_junctions.txt", 
		                     temp_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.sam", max_hits * 10, 
		                     temp_dir + "unspliced_mapped_sorted.multiple.unique_mapped.sam",
		                     logging_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.stat",
		                     logging_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.log")

	if junction_tobe_syn == "":
	    print >> sys.stderr, "[%s] Filtering junctions" % (right_now())
	    
	    filterjuncbysmalldeletion(original_dir + "ori.all_junctions.txt", 0, original_dir + "ori_all_junctions.smalldeletion.txt", 
		                      temp_dir + "ori.all_junctions.not_in_smalldeletion.txt", logging_dir + "filterori.all_junctionsbysmalldeletion.log")
	    
	if collect_stat > 1:
	    countline(original_dir + "ori.all_junctions.txt", logging_dir + "countline.ori.all_junctions.log")
    
	maxmultiphits = max_hits * 10

	
	if junction_tobe_syn == "":
	    #-----------------remove duplication of single reads----------------------#
	    #modify
	    #####remove this, report won't have duplication
	    RemDup(original_spliced_sam_sorted, original_dir + "original.unique.sam", 
		   original_dir + "original.multiple.sam", logging_dir + "original.stat", logging_dir + "original.log")
	    
	    #-----------------filter splice mapping with canonical rate----------------------#
	    #modify
	    FilterReadsByCanonNoncanon(original_dir + "original.multiple.sam", original_dir + "ori.all_junctions.txt", 
		                       original_dir + "original.multiple_filter_canon.sam", 
		                       original_dir + "original.multiple_filter_noncanon.sam", 
		                       original_dir + "original.multiple_filter_noncanon_canon.sam",
		                       original_dir + "original.multiple_filter_ins.sam",
		                       logging_dir + "original_canon_noncanon.stat",
		                       logging_dir + "original_canon_noncanon.log")
	
	ori_sam_array = [original_dir + "original.unique.sam"] + [original_dir + "original.multiple_filter_canon.sam"]
	
	ori_tobe_filter_mul_sam = original_dir + "original.multiple_filter_canon.sam"
	
	#if pairend != "":
	    
	    #ori_single_sam = original_dir + "ori_single.sam"
	    
	    #ori_paired_sam = original_dir + "ori_paired.sam"	    
	    
	    #original_spliced_sam_sorted = original_dir + "ori_single.sam"
	
	if junction_tobe_syn == "":
	    if pairend != "":
		ori_filter_canons_array = [original_dir + "original.multiple_filter_canon.sam"] + [original_dir + "original.unique.sam"]
		
		ori_filter_canons_sam = merge_chromo_sams(ori_filter_canons_array, original_dir + "original_tobe_paired.sam", logging_dir + "original_tobe_paired.log")
		
		ori_filter_canons_sam_sorted = sort_segment_bwt1(original_dir + "original_tobe_paired.sam", original_dir + "original_tobe_paired_sortedbyidx.sam")
    
		FilterByParing(original_dir + "original_tobe_paired_sortedbyidx.sam", original_dir + "original_paired.sam", 
		                   original_dir + "original_fusion_paired.sam", original_dir + "original_single.sam", original_dir + "original_filtered.sam", 
		                   50000, logging_dir + "original_pair.stat", logging_dir + "original_pair.log")
		
		ori_sam_array = [original_dir + "original_paired.sam"] + [original_dir + "original_fusion_paired.sam"] + [original_dir + "original_single.sam"]
		
		sam2juncarray([original_dir + "ori_paired.sam",], original_dir + "ori.paired.junc.txt", 
		          chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "ori.paired.junc.log")
		
		sam2juncarray([original_dir + "ori_single.sam",], original_dir + "ori.single.junc.txt", 
		          chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "ori.single.junc.log")
		
		ori_notpaired_sam_array = [original_dir + "original_fusion_paired.sam"] + [original_dir + "original_single.sam"]
		
		ori_notpaired_sam = merge_chromo_sams(ori_notpaired_sam_array, original_dir + "original_notpaired.sam", logging_dir + "original_notpaired.log")
		
		ori_tobe_filter_mul_sam = sort_segment_bwt1(original_dir + "original_notpaired.sam", original_dir + "original_notpaired_sortedbyidx.sam")
	
	if junction_tobe_syn == "":
	    sam2juncarray(ori_sam_array, original_dir + "ori.filtered.canon.noncanon.junctions.txt", 
		          chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "sam2junc.ori.filtered.canon.noncanon.junctions.log")
	    
	    #-----------------filter splice unsplice mapping with mismatch quality score and overall score----------------------#
	    #modify
	    FilterMultipleMapped(ori_tobe_filter_mul_sam, original_dir + "ori.filtered.canon.noncanon.junctions.txt", 
		                     original_dir + "ori.filtered_multiple.sam", max_hits * 10, original_dir + "ori.filtered_multiple.unique_mapped.sam",
		                     logging_dir + "original_filter_multiple.stat",
		                     logging_dir + "original_filter_multiple.log")
	
	best_sam_array = [original_dir + "original.unique.sam"] + [original_dir + "ori.filtered_multiple.sam"] + [original_dir + "ori.filtered_multiple.unique_mapped.sam"]
	
	if pairend != "":
	    best_sam_array = [original_dir + "original_paired.sam"] + [original_dir + "ori.filtered_multiple.sam"] + [original_dir + "ori.filtered_multiple.unique_mapped.sam"]
	
	if junction_tobe_syn == "":
	    sam2juncarray(best_sam_array, filteredbest_dir + "best_junction_bef_filter.txt", chromosome_files_dir, 
		          maxlen, 1, 350000000, "", 1, logging_dir + "sam2junc.best_junction_bef_filter.log")
	
	if remap_mismatch > 3:
	    remap_mismatch = 3
	
	#----------------filter junctions----------------------#
	
	if junction_tobe_syn == "":
	    filter_junc_by_min_mis_lpq(filteredbest_dir + "best_junction_bef_filter.txt", filteredbest_dir + "best_junction_all.txt", 
		                           filteredbest_dir + "best_junction_filtered_by_min_mis_lpq.txt", 
		                           remap_mismatch, float(max_seg + 1) / float(10),
		                           logging_dir + "best_junction_filtered_by_min_mis_lpq.log")#
	
	if junction_tobe_syn == "":
	    entropy_weight = 0.097718
	    lpq_weight = 0.66478
	    ave_mis_weight = -0.21077
	    min_score = 0.619
	    filterjuncbyROCarguNoncanon(filteredbest_dir + "best_junction_all.txt", filteredbest_dir + "best_junction.txt",
		                filteredbest_dir + "best_junction_semi_non_canon_filtered_by_ROCargu.txt", entropy_weight, lpq_weight, ave_mis_weight, 
		                min_score, logging_dir + "best_junction_semi_non_canon_remained_ROC.log")
    
	if junction_tobe_syn == "":
	    if fullrunning == 0:
		#------------------if not full running model---------------------------#
		(best_canon, best_noncaon) = count_canon_noncanon(filteredbest_dir + "best_junction.txt", 
		                                        filteredbest_dir + "best_junction_canon.txt", 
		                                        filteredbest_dir + "best_junction_semi_non_canon.txt",
		                                        logging_dir + "best_junction_canon_noncanon.log")
    
		filter_junc_by_min_mis_lpq(filteredbest_dir + "best_junction_semi_non_canon.txt", filteredbest_dir + "best_junction_semi_non_canon_remained.txt", 
		                           filteredbest_dir + "best_junction_semi_non_canon_filtered_by_min_mis_lpq.txt", 1, float(max_seg + 6) / float(10),
		                           logging_dir + "best_junction_semi_non_canon.log")#
		
		#------------------convert to bed format---------------------------#
		
		junc2bed2(filteredbest_dir + "best_junction_semi_non_canon_remained.txt", filteredbest_dir + "best_junction_canon.txt", 
		          filteredbest_dir + "best_junction_bef_filterbyjun.bed", logging_dir + "best_junction.bed.log")
	
		tobe_filtered_by_junc_sams = best_sam_array#[temp_dir + "best_remapped_bef_filterbyjun.sam"]
		
		FilterSamByJunc(tobe_filtered_by_junc_sams, filteredbest_dir + "best_junction_bef_filterbyjun.bed", filteredbest_dir + "best_mapped_filterbyjunc.sam", 
		                temp_dir + "best_mapped_filterbyjunc_filtered.sam", logging_dir + "best_mapped_filterbyjunc.log")
    
		#------------------merge splice mapped reads---------------------------#
		#modify add unsplice mapped reads, filter by filtered junction
		
		#all_mapped_array = [filteredbest_dir + "best_mapped_filterbyjunc.sam"] + [temp_dir + "unspliced_mapped.sam"]
		
		all_mapped_array = [filteredbest_dir + "best_mapped_filterbyjunc.sam"]
		
		if map_segment_directly == 0:
		    all_mapped_array = all_mapped_array + [temp_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.sam"]
		    all_mapped_array = all_mapped_array + [temp_dir + "unspliced_mapped_sorted.multiple.unique_mapped.sam"]
		    all_mapped_array = all_mapped_array + [temp_dir + "unspliced_mapped_sorted.unique.sam"]
		else:
		    all_mapped_array = all_mapped_array + [temp_dir + "unspliced_mapped.sam"]
	
		merge_chromo_sams(all_mapped_array, filteredbest_dir + "best_mapped.sam", logging_dir + "best_mapped.log")
		
		filtered_sam_array2 = [filteredbest_dir + "best_mapped.sam"]
		
		sam2juncarray(filtered_sam_array2, filteredbest_dir + "best_junction2.txt", 
		          chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "best_junction2.log")
		
		junc2bed(filteredbest_dir + "best_junction2.txt", output_dir + "best_junction.bed", logging_dir + "best_junction.log")
		
		sort_segment_bwt1(filteredbest_dir + "best_mapped.sam", filteredbest_dir + "best_mapped_sortedbyidx.sam")
		
		AddTagsToSam(filteredbest_dir + "best_mapped_sortedbyidx.sam", filteredbest_dir + "best_mapped_sortedbyidx_add_tags.sam", 
		             pairend, temp_dir + "merged_paired_reads", 
		             filteredbest_dir + "unmapped.sam", logging_dir + "best_mapped_sortedbyidx_add_tags.stat", 
		             format_flag, max_insert, filteredbest_dir + "best_junction2.txt", 
		             chromo_size_file, logging_dir + "best_mapped_sortedbyidx_add_tags.log")
		
		files_tobe_cat = [filteredbest_dir + "best_mapped_sortedbyidx_add_tags.sam.head"] + [filteredbest_dir + "best_mapped_sortedbyidx_add_tags.sam.forward"] + [filteredbest_dir + "best_mapped_sortedbyidx_add_tags.sam.reverse"] + [filteredbest_dir + "unmapped.sam"]
		
		cat_files(files_tobe_cat, output_dir + "alignments.sam")
		
		if fullrunning == 0 and pairend != "" and run_mapper > 0:
		    #---------------merge mapped reads for pairing---------------------#
		    #modify
		    paired_sams = [filteredbest_dir + "best_mapped_sortedbyidx.sam"]# + [temp_dir + "unspliced_mapped.sam"]# + [original_dir + "original_spliced.unspliced.sam"]
		    
		    if do_fusion == 1:
			paired_sams = paired_sams + [fusion_dir + "original_fusion.sam"]
		    
		    ###paired_sams = paired_sams + [sam_output_file] + [fusion_output_file]		
		    
		    tobe_paired_sam = merge_chromo_sams(paired_sams, temp_dir + "merged_tobepaired.sam", logging_dir + "merged_tobepaired.log")
			
		    merged_paied_sorted_sams = sort_segment_bwt1(tobe_paired_sam, temp_dir + "merged_tobepaired_sorted.sam")
		
		    #-------------pair mapped reads---------------------#
		    pairsam(merged_paied_sorted_sams, temp_dir + "merged_paired.sam", 
			    temp_dir + "merged_single.sam", "", 10, logging_dir + "pair_sam_best.log")
    
		    #-------------Run mapper----------------------------#
		    runPER(temp_dir + "merged_paired.sam", temp_dir + "merged_single.sam")
		    
		    fusion_per_prob_sams = read_dir_by_suffix(fusion_result_PER_prob_dir, "sam")
		    
		    prob_alignment = merge_chromo_sams(fusion_per_prob_sams, output_dir + "prob_alignment.sam", logging_dir + "prob_alignment.log")
		    
		    sam2juncarray(fusion_per_prob_sams, output_dir + "prob_junction.txt", chromosome_files_dir, 
			  2000, 0, 350000000, "", 1, logging_dir + "prob_junction.log")

	if collect_stat > 1:
	    countline(filteredbest_dir + "best_junction.txt", logging_dir + "best_junction.log")    
	    
	if fullrunning > 0:
	    #------------------merge splice mapped reads---------------------------#
	    #modify add unsplice mapped reads, filter by filtered junction
	    
	    if junction_tobe_syn != "":
		filter_junc_by_min_mis_lpq(junction_tobe_syn, junction_tobe_syn + ".filtered.minmis.lpq", 
		                               junction_tobe_syn + ".filteredout.minmis.lpq.txt", 
		                               remap_mismatch, float(max_seg + 1) / float(10),
		                               logging_dir + "filteredout.minmis.lpq.log")#
		
		junction_tobe_syn = junction_tobe_syn + ".filtered.minmis.lpq"
    
		entropy_weight = 0.097718
		lpq_weight = 0.66478
		ave_mis_weight = -0.21077
		min_score = 0.619
		filterjuncbyROCarguNoncanon(junction_tobe_syn, junction_tobe_syn + ".filtered.roc.txt",
		                    junction_tobe_syn + ".filteredout.roc.txt", entropy_weight, lpq_weight, ave_mis_weight, 
		                    min_score, logging_dir + "filteredout.roc.txt.log")
	    
		junction_tobe_syn = junction_tobe_syn + ".filtered.roc.txt"
		
	    if junction_tobe_syn == "":
		if map_segment_directly == 0:
		    best_sam_array = best_sam_array + [temp_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.sam"]
		    best_sam_array = best_sam_array + [temp_dir + "unspliced_mapped_sorted.multiple.unique_mapped.sam"]
		    best_sam_array = best_sam_array + [temp_dir + "unspliced_mapped_sorted.unique.sam"]
		else:
		    best_sam_array = best_sam_array + [temp_dir + "unspliced_mapped.sam"]
		    
		merge_chromo_sams(best_sam_array, filteredbest_dir + "best_mapped.sam", logging_dir + "best_mapped.log")
		
		#-----------------Separate spliced unspliced mapped reads---------------------#
		SepSplicedUnSpliced(filteredbest_dir + "best_mapped.sam", filteredbest_dir + "best_spliced.sam", 
		                    filteredbest_dir + "best_unspliced.sam", 
		                    logging_dir + "best_mapped.sam.stat", logging_dir + "SepSplicedUnSpliced_best_mapped.log")
		
		#-----------------full running model---------------------#
		filterjuncbysmalldeletion(filteredbest_dir + "best_junction.txt", 0, filteredbest_dir + "best_junction.txt.smalldeletion", 
		                          filteredbest_dir + "best_junction.txt.not_in_smalldeletion",
		                          logging_dir + "filter_best_junction_by_samlldeletion.txt")
		
		junction_tobe_syn = filteredbest_dir + "best_junction.txt.not_in_smalldeletion"

	    #-----------------synthetic junction sequence---------------------#
	    
	    
		
	    junc_db(junction_tobe_syn, chromosome_files_dir, min_anchor_length, 
		    maxlen - 1, 50, remap_dir + "synthetic_alljunc_sequenc.txt",
		    logging_dir + "junc_db.log")
	    
	    #-----------------build junction sequence index---------------------#
	    check_bowtie_index(remap_dir + "syn_idx_prefix", remap_dir + "synthetic_alljunc_sequenc.txt", params.rerun_all, FASTA_file_extension)
	    
	    syn_idx_prefix = remap_dir + "syn_idx_prefix"
	    
	    if remap_mismatch > 3:
		remap_mismatch = 3
	
	    write_current_stats("Remapping spliced reads")
	    
	    #-----------------remap to junction sequence---------------------#
	    (syn_bwt_map, syn_temp_unmapped_reads) = bowtie(syn_idx_prefix, 
						       unmapped_reads,
						       format_flag, 
						       "syn_unspliced_map.bwtout",
						       "syn_unmapped.fa",
						       bowtie_threads,
						       maxlen - 2,
						       50,
						       remap_dir + "syn_repeat_reads.fa",
						       remap_mismatch,
						       logging_dir + "remapped_reads.log")
	
	    #-----------------convert to sam file---------------------#
	    juncdb_bwt2sam(syn_bwt_map, 0, remap_dir + "syn_remapped.sam", logging_dir + "syn_remapped.log")
	    
	    syn_remapped_sorted = remap_dir + "syn_remapped.sam"
	    
	    #if do_fusion >= 1:
		
		#syn_fusion_junc_seq(output_dir + "fusion.junction", fusion_dir + "fusion.synseq", 
		#		    chromosome_files_dir, read_width - 1, logging_dir + "syn_fusion_seq.log")
		
		#check_bowtie_index(fusion_dir + "fusion_syn_idx_prefix", fusion_dir + "fusion.synseq", rerun_all, FASTA_file_extension)
		
		#fusion_syn_idx_prefix = fusion_dir + "fusion_syn_idx_prefix"
		
		#(fusion_syn_bwt_map, fusion_syn_temp_unmapped_reads) = bowtie(fusion_syn_idx_prefix, 
		#				       syn_temp_unmapped_reads,
		#				       format_flag, 
		#				       "fusion_syn_unspliced_map.bwtout",
		#				       "fusion_syn_unmapped.fa",
		#				       bowtie_threads,
		#				       read_width - 2,
		#				       50,
		#				       fusion_dir + "fusion_syn_repeat_reads.fa",
		#				       remap_mismatch,
		#				       logging_dir + "fusion_remapped_reads.log")
		
		#FusionBWA2FusionSam(fusion_syn_bwt_map, fusion_dir + "fusion_remap_sam", read_width - 1, logging_dir + "FusionBWA2FusionSam.log")

	    	#remap_fusion_sam_sorted = sort_segment_bwt1(fusion_dir + "fusion_remap_sam", fusion_dir + "fusion_remap_sam.sorted")
	    
	    	##----------------filter multiple mapping fusion reads----------------------#
	     
	    	#separatedmultipleuniquefusion(fusion_dir + "fusion_remap_sam.sorted", output_dir + "fusion.remapped.unique", 
		#			  fusion_dir + "fusion.remapped.multiple", logging_dir + "fusion_remapped.stat")
	
	    	##----------------convert to fusion junction----------------------#
	    	#fusionsam2juncplus1(output_dir + "fusion.remapped.unique", output_dir + "fusion_remap_junction.unique", read_width, "", 
		#	    	logging_dir + "fusionsam2junc_remap_unique.log")

		#filterfusionjuncbystartend(filteredbest_dir + "best_junction.txt.not_in_smalldeletion", output_dir + "fusion_remap_junction.unique", output_dir + "fusion_remap_junction.unique.root", 10, logging_dir + "filterfusionjuncbystartend.log")
	    
	    if bowtie_threads > 1:
		syn_remapped_sorted = sort_segment_bwt1(remap_dir + "syn_remapped.sam", 
						remap_dir + "syn_remapped_sorted.sam")
	    
	    #-------------------remove duplication--------------------#
	    RemDup(syn_remapped_sorted, remap_dir + "syn_remapped_sorted.unique.sam", 
		   remap_dir + "syn_remapped_sorted.multiple.sam", logging_dir + "syn_remapped_sorted.stat", logging_dir + "syn_remapped_sorted.log")
	    
	    #modify
	    FilterReadsByCanonNoncanon(remap_dir + "syn_remapped_sorted.multiple.sam", filteredbest_dir + "best_junction.txt", 
				       remap_dir + "syn_remapped_sorted.multiple.filter_canon.sam", 
				       remap_dir + "syn_remapped_sorted.multiple.noncanon.sam", 
				       remap_dir + "syn_remapped_sorted.multiple.noncanon_canon.sam",
				       remap_dir + "syn_remapped_sorted.multiple.ins.sam",
				       logging_dir + "filtercanon_noncanon_syn_remapped_sorted.stat",
				       logging_dir + "filtercanon_noncanon_syn_remapped_sorted.log")
	    
	    remap_ori_spliced_unspliced_sams = [remap_dir + "syn_remapped_sorted.unique.sam"] + [remap_dir + "syn_remapped_sorted.multiple.filter_canon.sam"] + [filteredbest_dir + "best_unspliced.sam"]
	    
	    remapped_ori_sam = merge_chromo_sams(remap_ori_spliced_unspliced_sams, remap_dir + "remap_ori_spliced_unspliced.sam", logging_dir + "remap_ori_spliced_unspliced.log")
	    
	    syn_remapped_sorted = sort_segment_bwt1(remap_dir + "remap_ori_spliced_unspliced.sam", remap_dir + "remap_ori_spliced_unspliced_sorted_byname.sam")
	    
	    if pairend != "":
		#--------------------pair end reads---------------------#
		
		#--------------------pairing mapped reads--------------------#
		FilterByParing(remap_dir + "remap_ori_spliced_unspliced_sorted_byname.sam", remap_dir + "remapped_paired.sam", 
			       remap_dir + "remapped_fusion_paired.sam", remap_dir + "remapped_single.sam", remap_dir + "remapped_filtered.sam", 
			       50000, logging_dir + "remap_pair.stat", logging_dir + "remapped_pair.log")
		
		RemDup(remap_dir + "remapped_filtered.sam", remap_dir + "remapped_filtered.unique.sam", 
		   remap_dir + "remapped_filtered.multiple.sam", logging_dir + "remapped_filtered.stat", logging_dir + "remapped_filtered.log")
		
		fusion_paired_sam = remap_dir + "remapped_fusion_paired.sam"
	    
		real_single_sam = remap_dir + "remapped_single.sam"
		
		region_file = cluster_result_dir + "cluster.txt"
		
		if do_cluster > 0:
		    #--------------------cluster--------------------#
		    parseCluster(fusion_paired_sam, cluster_dir, logging_dir + "remap_parseCluster.log")
		    
		    #--------------------generate cluster region--------------------#
		    cluster(cluster_dir, logging_dir + "remap_cluster.log")

		    merge_sort_segment_bwt1(fusion_dir + "fusion_head.txt", fusion_dir + "fusion_tail.txt", fusion_dir + "fusion_single_anchored_merged_sorted.txt")

		    fusion_candidate_file = fusion_dir + "fusion_single_anchored_merged_sorted.txt"

		    fusion_remained_candidate_file = FilterFusionCandidatesByClusterRegions(region_file, 
		                                         real_single_sam, fusion_candidate_file, 10000, num_seg, 
		                                         logging_dir + "remap_FilterFusionCandidatesByClusterRegions.log")

		    merge_sort_segment_bwt2(fusion_remained_candidate_file, fusion_remained_candidate_file + ".chrom.sorted")

		    load_fusion_single_anchor_chrom_seq(fusion_remained_candidate_file + ".chrom.sorted", fusion_remained_candidate_file + ".chrom.sorted.loaded", chromosome_files_dir, logging_dir + "load_fusion_single_anchor_chrom_seq.log")

		    #-----------------fill missed segment for fusion------------------------#
		    juncs_file = call_mapsplice_segment_fusion_single_anchor(islands_file, 
					seed_length,
					maxlen,
					min_anchor_length,
					splice_mismatches,
					1,
					max_intron_length,
					island_extension,
					fusion_flank_case,
					0.0,
					FASTA_file_extension,
					divided_reads,
					chromosome_files_dir,
					num_anchor,
					num_seg,
					seg_len,
					bwt_map_25,
					fix_hole_file,
					output_dir,
					Fqunmapped,
					extend_bits,
					total_mismatch,
					total_fusion_mismatch,
					append_mismatch,
					prefix_match,
					2,
					fusion_dir + "original_fusion_junction",
					fusion_remained_candidate_file + ".chrom.sorted.loaded")
	    
		    fusion_fixed = read_dir_by_suffix(fusion_dir, "fixed")
	    
		    original_fusion_sam = merge_chromo_sams(fusion_fixed, fusion_dir + "original_fusion.sam", 
		                                            logging_dir + "original_fusion.log")
	    
		    original_fusion_sam_sorted = sort_segment_bwt1(fusion_dir + "original_fusion.sam", 
		                                                   fusion_dir + "original_fusion.sam.sorted")
	    
		    RemDup(fusion_dir + "original_fusion.sam.sorted", output_dir + "fusion.mapped.unique", 
		           fusion_dir + "original_fusion.sam.sorted.multiple", logging_dir + "original_fusion.sam.sorted.stat", 
		           logging_dir + "original_fusion.sam.sorted.log")

		    fusion_ori_rem_dup = [output_dir + "fusion.mapped.unique"] + [fusion_dir + "original_fusion.sam.sorted.multiple"]
		    
		    fusion_ori_rem_dup_sam = merge_chromo_sams(fusion_ori_rem_dup, fusion_dir + "fusion_ori_rem_dup.sam", 
		                                               logging_dir + "fusion_ori_rem_dup.log")
	    
		    fusion_ori_rem_dup_sam_sorted = sort_segment_bwt1(fusion_ori_rem_dup_sam, fusion_ori_rem_dup_sam + ".sorted")
	    
		    pairing_fusion_normal_aligned(region_file, real_single_sam, fusion_ori_rem_dup_sam_sorted, 
		                                  10000, logging_dir + "pairing_fusion_normal_aligned.log")
		    
		    #----------------filter multiple mapping fusion reads----------------------#
	     
		    #separatedmultipleuniquefusion(fusion_dir + "original_fusion.sam.sorted", output_dir + "fusion.mapped.unique", 
			#		  fusion_dir + "original_fusion.sam.sorted.multiple", logging_dir + "fusion.stat")
	
		    #----------------convert to fusion junction----------------------#
		    fusionsam2junc1(output_dir + "fusion.mapped.unique", fusion_dir + "fusion_junction.unique", maxlen, "", 
			    logging_dir + "fusionsam2junc_unique.log")

		    fusionsam2junc1(fusion_ori_rem_dup_sam_sorted, output_dir + "fusion.junction", maxlen, "", 
			    logging_dir + "fusionsam2junc_unique.log")
	
		    #filterfusionjuncbyminmis(fusion_dir + "fusion_junction.unique", 1, output_dir + "fusion.junction",
				     #fusion_dir + "fusion.unique.junction.not_in_min_mis", logging_dir + "filter_fusion_by_minmis.log")
       
		    ###output_dir_file = cluster_dir + "output_dir_file"
		    
		    #--------------------combine cluster region sequence, generate input reads--------------------#
		    ###ReadRegions(region_file, real_single_sam, temp_unmapped_reads, cluster_dir, format_flag, chromosome_files_dir, 
		    ###		output_dir_file, 5000, logging_dir + "remap_read_regions.log")
		    
		    ###cmd_format = "fa"
		    ###if format_flag == '-q':
			###cmd_format = "fq"
		    ###arguments = "\"--max-hits " arguments = arguments + str(max_hits)
		    ###arguments = arguments + " -X " arguments = arguments + str(bowtie_threads) 
		    ###arguments = arguments + " -n "arguments = arguments + str(min_anchor_length)
		    ###arguments = arguments + " -w "arguments = arguments + str(maxlen)
		    ###arguments = arguments + " -S "arguments = arguments + FASTA_file_extension
		    ###arguments = arguments + " -Q "arguments = arguments + cmd_format
		    ###arguments = arguments + " -L "arguments = arguments + str(seg_len)
		    ###arguments = arguments + " --not-rem-temp\""
		    
		    ###bash_file = cluster_dir + "mps_bash_file"
		    
		    #-------------------generate bash file and run--------------------#
		    ###generate_bash_file_and_run(output_dir_file, bash_file, "/", arguments, bin_dir, logging_dir + "remap_generate_bash_file_and_run.log")
		    
		    ###sam_output_file = fusion_dir + "cluster.sam"
		    
		    ###fusion_output_file = output_dir + "cluster.fusion.mapped"		
		    
		    #-------------------convert to absolute offset--------------------#
		    ###convert_to_abs_offset(output_dir_file, sam_output_file, fusion_output_file, "/", logging_dir + "convert_to_abs_offset.log")
		    
		    ###fusionsam2junc1(fusion_output_file, fusion_dir + "cluster.fusion.ori.junction", read_width, "", 
			    ###logging_dir + "cluster.fusion.ori.junction.log")
		    
		    ###filterfusionjuncbyminmis(fusion_dir + "cluster.fusion.ori.junction", 1, output_dir + "cluster.fusion.junction",
				     ###fusion_dir + "fusion.unique.junction.not_in_min_mis", logging_dir + "cluster.fusion.junction.log")
		
		#-------------------remove duplication of paired reads--------------------#
		#modify
		RemDup(remap_dir + "remapped_paired.sam", remap_dir + "remapped_paired.unique.sam", 
		   remap_dir + "remapped_paired.multiple.sam", logging_dir + "remapped_paired.stat", logging_dir + "remapped_paired.log")
		
		remapped_tobe_filetered_sams = [remap_dir + "remapped_fusion_paired.sam"] + [remap_dir + "remapped_single.sam"]
		
		#if do_cluster > 0:
		    #remapped_tobe_filetered_sams = remapped_tobe_filetered_sams + [sam_output_file]
		
		merge_chromo_sams(remapped_tobe_filetered_sams, remap_dir + "remapped_tobe_filtered.sam", 
		                  logging_dir + "remapped_tobe_filtered.log")
		
		#-------------------merge single mapped reads for filtering--------------------#
		sort_segment_bwt1(remap_dir + "remapped_tobe_filtered.sam", remap_dir + "remapped_tobe_filtered_sortbyname.sam")
		
		syn_remapped_sorted = remap_dir + "remapped_tobe_filtered_sortbyname.sam"
	    
	    #-------------------remove duplication--------------------#
	    #modify
	    
	    RemDup(syn_remapped_sorted, remap_dir + "syn_remapped.unique.sam",
		   remap_dir + "syn_remapped.multiple.sam", logging_dir + "rmdup.syn_remapped.stat", 
		   logging_dir + "rmdup.syn_remapped.log")
	    
	    ##################move down######################################
	    #if pairend != "" and run_mapper > 0:
		##--------------pairing mapped reads for MapPer-----------------#
		##modify
		#paired_sams = [remap_dir + "remapped_filtered.unique.sam"] + [remap_dir + "remapped_filtered.multiple.sam"] + [remap_dir + "syn_remapped.unique.sam"] 
		
		#paired_sams = paired_sams + [remap_dir + "syn_remapped.multiple.sam"] + [remap_dir + "remapped_paired.unique.sam"] + [remap_dir + "remapped_paired.multiple.sam"]
		
		#if do_fusion == 1:
		    #if do_cluster > 0:
			#paired_sams = paired_sams + [fusion_dir + "fusion_ori_rem_dup.sam.sorted"]
		    #else:
			#paired_sams = paired_sams + [fusion_dir + "original_fusion.sam"]
		
		##if do_cluster > 0:
		    ##paired_sams = paired_sams + [cluster_dir + "cluster.fusion.mapped"]
		
		####paired_sams = paired_sams + [sam_output_file] + [fusion_output_file]
		
		##--------------merge mapped reads and sort-----------------#
		#tobe_paired_sam = merge_chromo_sams(paired_sams, temp_dir + "merged_tobepaired.sam", logging_dir + "merged_tobepaired.log")
		
		#merged_paied_sorted_sams = sort_segment_bwt1(tobe_paired_sam, temp_dir + "merged_tobepaired_sorted.sam")
		
		##--------------pair mapped reads-----------------#
		#pairsam(merged_paied_sorted_sams, fusion_dir + "merged_paired.sam", fusion_dir + "merged_single.sam", 
			#"", 10, logging_dir + "pair_sam_remapped.log")
		
		####cluster(merge_pair_sam, output_file, log_file)
		
		##--------------run MapPer-----------------#
		#runPER(fusion_dir + "merged_paired.sam", fusion_dir + "merged_single.sam")
		
		#fusion_per_prob_sams = read_dir_by_suffix(fusion_result_PER_prob_dir, "sam")
		
		#prob_alignment = merge_chromo_sams(fusion_per_prob_sams, output_dir + "prob_alignment.sam", logging_dir + "prob_alignment.log")
		
		#sam2juncarray(fusion_per_prob_sams, output_dir + "prob_junction.txt", chromosome_files_dir, 
		      #2000, 0, 350000000, "", 1, logging_dir + "prob_junction.log")
	    
	    #-----------------filter spliced mapped read by canonical rate-----------------#
	    #modify
	    FilterReadsByCanonNoncanon(remap_dir + "syn_remapped.multiple.sam", filteredbest_dir + "best_junction.txt", 
				       remap_dir + "syn_remapped.multiple.filter_canon.sam", 
				       remap_dir + "syn_remapped.multiple.noncanon.sam", 
				       remap_dir + "syn_remapped.multiple.noncanon_canon.sam",
				       remap_dir + "syn_remapped.multiple.ins.sam",
				       logging_dir + "filtercanon_noncanon_syn_remapped.stat",
				       logging_dir + "filtercanon_noncanon_syn_remapped.log")
	
	    remapped_sam_array = [remap_dir + "syn_remapped.unique.sam"] + [remap_dir + "syn_remapped.multiple.filter_canon.sam"]
	    
	    if pairend != "":
		remapped_sam_array = remapped_sam_array + [remap_dir + "remapped_paired.unique.sam"] + [remap_dir + "remapped_paired.multiple.sam"]
		
	    sam2juncarray(remapped_sam_array, remap_dir + "syn.remdup_filter_canon_all_junctions.txt",
		      chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "syn.remdup_filter_canon_all_junctions.log")
	    
	    #-----------------filter multiple splice unsplice mapping with mismatch quality score and overall score-----------------#
	    #modify
	    FilterMultipleMapped(remap_dir + "syn_remapped.multiple.filter_canon.sam", remap_dir + "syn.remdup_filter_canon_all_junctions.txt", 
				remap_dir + "syn.filtered_multiple.sam", max_hits * 10, remap_dir + "syn.unique_mapped.sam",
				logging_dir + "filtermultiple_syn_remapped.stat", logging_dir + "filtermultiple_syn_remapped.log")

	    #--------------single mapped reads-------------------------#
	    filterd_remapped_sam_array = [remap_dir + "syn_remapped.unique.sam"] + [remap_dir + "syn.filtered_multiple.sam"]

	    filterd_remapped_sam_array = filterd_remapped_sam_array + [remap_dir + "syn.unique_mapped.sam"]# + [filteredbest_dir + "best_unspliced.sam"]
	    
	    #filterd_remapped_sam_array = filterd_remapped_sam_array + [temp_dir + "unspliced_mapped.sam"]
	    
	    #if map_segment_directly == 0:
		#filterd_remapped_sam_array = filterd_remapped_sam_array + [temp_dir + "unspliced_mapped_sorted.multiple.filtered_multiple.sam"]
		#filterd_remapped_sam_array = filterd_remapped_sam_array + [temp_dir + "unspliced_mapped_sorted.multiple.unique_mapped.sam"]
		#filterd_remapped_sam_array = filterd_remapped_sam_array + [temp_dir + "unspliced_mapped_sorted.unique.sam"]
	    #else:
		#filterd_remapped_sam_array = filterd_remapped_sam_array + [temp_dir + "unspliced_mapped.sam"]

	    if pairend != "":
		#--------------paired mapped reads-------------------------#
		filterd_remapped_sam_array = filterd_remapped_sam_array + [remap_dir + "remapped_paired.unique.sam"] + [remap_dir + "remapped_paired.multiple.sam"]
		
	    merge_chromo_sams(filterd_remapped_sam_array, temp_dir + "best_remapped_bef_filterbyjun.sam", logging_dir + "best_remapped_bef_filterbyjun.log")
	    
	    sam2juncarray(filterd_remapped_sam_array, filteredbest_dir + "best_syn_bef_filter_junction.txt", 
		      chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "best_syn_bef_filter_junction.log")
	    
	    filter_junc_by_min_mis_lpq(filteredbest_dir + "best_syn_bef_filter_junction.txt", filteredbest_dir + "best_syn_junction.txt", 
				       filteredbest_dir + "best_syn_junction_filtered_by_min_mis_lpq.txt", 
				       remap_mismatch, float(max_seg + 1) / float(10), logging_dir + "filter_by_min_mis_best_syn_junction.log")#
	
	    (best_syn_canon, best_syn_noncaon) = count_canon_noncanon(filteredbest_dir + "best_syn_junction.txt", 
						    filteredbest_dir + "best_syn_junction_canon.txt", 
						    filteredbest_dir + "best_syn_junction_semi_non_canon.txt",
						    logging_dir + "best_syn_junction_canon_noncanon.log")	    
	    
	    #--------------filter noncanonical junction -------------------------#
	    filter_junc_by_min_mis_lpq(filteredbest_dir + "best_syn_junction_semi_non_canon.txt", filteredbest_dir + "best_syn_junction_semi_non_canon_remained.txt", 
				       filteredbest_dir + "best_syn_junction_semi_non_canon_filtered_by_min_mis_lpq.txt", 1, float(max_seg + 6) / float(10),
				       logging_dir + "best_syn_junction_semi_non_canon.log")#
	    
	    #--------------convert junction to bed format-------------------------#
	    junc2bed2(filteredbest_dir + "best_syn_junction_semi_non_canon_remained.txt", filteredbest_dir + "best_syn_junction_canon.txt", 
		      filteredbest_dir + "best_remapped_junction_bef_filter_sam.bed", logging_dir + "best_syn_junction_semi_non_canon_remained_bef_filter_sam.log")
	    
	    tobe_filtered_by_junc_sams = [temp_dir + "best_remapped_bef_filterbyjun.sam"]
	    
	    #--------------filter sam by filtered junction-------------------------#
	    FilterSamByJunc(tobe_filtered_by_junc_sams, filteredbest_dir + "best_remapped_junction_bef_filter_sam.bed", filteredbest_dir + "best_remapped.sam", temp_dir + "best_remapped_filtered.sam", logging_dir + "filter_best_remapped_by_junc.log")
	    
	    filtered_remapped_sam_array2 = [filteredbest_dir + "best_remapped.sam"]
	    
	    sam2juncarray(filtered_remapped_sam_array2, filteredbest_dir + "best_remapped_junction2.txt", 
		      chromosome_files_dir, maxlen, 1, 350000000, "", 1, logging_dir + "best_remapped_junction.log")
	    
	    if pairend != "":
		sam2juncarray_paired(filtered_remapped_sam_array2, remap_dir + "best_remapped_junction_paired.txt", 
			  chromosome_files_dir, maxlen, 1, 350000000, "", 1, "=", logging_dir + "best_remapped_junction_paired.log")
		
		sam2juncarray_paired(filtered_remapped_sam_array2, remap_dir + "best_remapped_junction_single.txt", 
			  chromosome_files_dir, maxlen, 1, 350000000, "", 1, "*",logging_dir + "best_remapped_junction_single.log")
	    
	    #--------------regenerate bed file after filter sam-------------------------#
	    junc2bed(filteredbest_dir + "best_remapped_junction2.txt", output_dir + "best_remapped_junction.bed", logging_dir + "best_remapped_junction.log")
	    
	    sort_segment_bwt1(filteredbest_dir + "best_remapped.sam", filteredbest_dir + "best_remapped_sortedbyidx.sam")
	    
	    AddTagsToSam(filteredbest_dir + "best_remapped_sortedbyidx.sam", filteredbest_dir + "best_remapped_sortedbyidx_add_tags.sam", 
			 pairend, temp_dir + "merged_paired_reads", 
			 filteredbest_dir + "unmapped.sam", logging_dir + "best_remapped_sortedbyidx_add_tags.stat", 
			 format_flag, max_insert, filteredbest_dir + "best_remapped_junction2.txt", 
	                 chromo_size_file,
	                 logging_dir + "best_remapped_sortedbyidx_add_tags.log")
	    
	    files_tobe_cat = [filteredbest_dir + "best_remapped_sortedbyidx_add_tags.sam.head"] + [filteredbest_dir + "best_remapped_sortedbyidx_add_tags.sam.forward"] + [filteredbest_dir + "best_remapped_sortedbyidx_add_tags.sam.reverse"] + [filteredbest_dir + "unmapped.sam"]
	    
	    cat_files(files_tobe_cat, output_dir + "alignments.sam")

	    if do_fusion >= 1:

	    	fusion_read_files_dir = sam2fq(filteredbest_dir + "unmapped.sam.indexed", 
		                                   filteredbest_dir + "unmapped.fq", "1", 
		                                   logging_dir + "fusion_sam2fq.log")

		fusion_junc_db(filteredbest_dir + "best_junction.txt.not_in_smalldeletion", 
		               output_dir + "fusion.junction",
		               chromosome_files_dir, min_anchor_length, 
		               maxlen - 1, 50, fusion_dir + "fusion.synseq",
		               logging_dir + "junc_db.log")
		
		#syn_fusion_junc_seq(output_dir + "fusion.junction", fusion_dir + "fusion.synseq", 
				    #chromosome_files_dir, read_width - 1, logging_dir + "syn_fusion_seq.log")
		
		check_bowtie_index(fusion_dir + "fusion_syn_idx_prefix", fusion_dir + "fusion.synseq", params.rerun_all, FASTA_file_extension)
		
		fusion_syn_idx_prefix = fusion_dir + "fusion_syn_idx_prefix"
		
		(fusion_syn_bwt_map, fusion_syn_temp_unmapped_reads) = bowtie(fusion_syn_idx_prefix, 
						       fusion_read_files_dir,
						       "-q", 
						       "fusion_syn_unspliced_map.bwtout",
						       "fusion_syn_unmapped.fa",
						       bowtie_threads,
						       maxlen - 2,
						       50,
						       fusion_dir + "fusion_syn_repeat_reads.fa",
						       remap_mismatch,
						       logging_dir + "fusion_remapped_reads.log")
		
		replace_fusion_seq(fusion_syn_bwt_map, fusion_syn_bwt_map + ".replaced", 
		                   fusion_dir + "fusion.synseq", logging_dir + "replace_fusion_seq.log")
		
		#-----------------convert to sam file---------------------#
		juncdb_fusion_bwt2sam(fusion_syn_bwt_map + ".replaced", 0, fusion_dir + "fusion_remap_sam", 
		                      maxlen - 1, logging_dir + "juncdb_fusion_bwt2sam.log")
		
		#FusionBWA2FusionSam(fusion_syn_bwt_map, fusion_dir + "fusion_remap_sam", read_width - 1, logging_dir + "FusionBWA2FusionSam.log")

	    	remap_fusion_sam_sorted = sort_segment_bwt1(fusion_dir + "fusion_remap_sam", fusion_dir + "fusion_remap_sam.sorted")
	    
		separateuniquefusion_newfmt(fusion_dir + "fusion_remap_sam.sorted", output_dir + "fusion.remapped.unique", 
					  fusion_dir + "fusion.remapped.multiple", logging_dir + "fusion_remapped.stat")
		
	    if pairend != "" and run_mapper > 0:
		#--------------pairing mapped reads for MapPer-----------------#
		#modify
		paired_sams = [remap_dir + "remapped_filtered.unique.sam"] + [remap_dir + "remapped_filtered.multiple.sam"] + [remap_dir + "syn_remapped.unique.sam"] 
		
		paired_sams = paired_sams + [remap_dir + "syn_remapped.multiple.sam"] + [remap_dir + "remapped_paired.unique.sam"] + [remap_dir + "remapped_paired.multiple.sam"]
		
		if do_fusion == 1:
		    if do_cluster > 0:
			paired_sams = paired_sams + [output_dir + "fusion.remapped.unique"] + [fusion_dir + "fusion.remapped.multiple"]
		    else:
			paired_sams = paired_sams + [output_dir + "fusion.remapped.unique"] + [fusion_dir + "fusion.remapped.multiple"]
		
		#if do_cluster > 0:
		    #paired_sams = paired_sams + [cluster_dir + "cluster.fusion.mapped"]
		
		###paired_sams = paired_sams + [sam_output_file] + [fusion_output_file]
		
		#--------------merge mapped reads and sort-----------------#
		tobe_paired_sam = merge_chromo_sams(paired_sams, temp_dir + "merged_tobepaired.sam", logging_dir + "merged_tobepaired.log")
		
		merged_paied_sorted_sams = sort_segment_bwt1(tobe_paired_sam, temp_dir + "merged_tobepaired_sorted.sam")
		
		#--------------pair mapped reads-----------------#
		pairsam(merged_paied_sorted_sams, fusion_dir + "merged_paired.sam", fusion_dir + "merged_single.sam", 
	                "", 10, logging_dir + "pair_sam_remapped.log")
		
		###cluster(merge_pair_sam, output_file, log_file)
		
		#--------------run MapPer-----------------#
		runPER(fusion_dir + "merged_paired.sam", fusion_dir + "merged_single.sam")
		
		fusion_per_prob_sams = read_dir_by_suffix(fusion_result_PER_prob_dir, "sam")
		
		prob_alignment = merge_chromo_sams(fusion_per_prob_sams, output_dir + "prob_alignment.sam", logging_dir + "prob_alignment.log")
		
		sam2juncarray(fusion_per_prob_sams, output_dir + "prob_junction.txt", chromosome_files_dir, 
	              2000, 0, 350000000, "", 1, logging_dir + "prob_junction.log")
		    
	    	#----------------filter multiple mapping fusion reads----------------------#
	     
		
		
	    	#separatedmultipleuniquefusion(fusion_dir + "fusion_remap_sam.sorted", output_dir + "fusion.remapped.unique", 
					  #fusion_dir + "fusion.remapped.multiple", logging_dir + "fusion_remapped.stat")

	    	#fusionsam2maf(output_dir + "fusion.remapped.unique.maf", chromo_size_file, output_dir + "fusion.remapped.unique", logging_dir + "fusion.remapped.unique.maf.log")
	
	    	#----------------convert to fusion junction----------------------#
	    if do_fusion >= 1:
		fusionsam2junc_filteranchor_newfmt(output_dir + "fusion.remapped.unique", 
		                                output_dir + "fusion_remap_junction.unique.chr_seq.extracted", maxlen, "", 20, 
		                                chromosome_files_dir, logging_dir + "fusionsam2junc_remap_unique.log")

		#extract_fusion_chr_seq(fusion_dir + "fusion_remap_junction.unique", output_dir + "fusion_remap_junction.unique.chr_seq.extracted", chromosome_files_dir, read_width - 1, logging_dir + "extract_fusion_chr_seq.log")

		#filterfusionjuncbystartend(filteredbest_dir + "best_junction.txt.not_in_smalldeletion", output_dir + "fusion_remap_junction.unique.chr_seq.extracted", output_dir + "fusion_remap_junction.unique.chr_seq.extracted.root", 10, logging_dir + "filterfusionjuncbystartend.log")
	    
		if do_filter_fusion_by_repeat > 0:
		    filter_fusion_by_repeat(output_dir + "fusion_remap_junction.unique.chr_seq.extracted", 
			                    output_dir + "fusion_remap_junction.unique.chr_seq.out", 
			                    output_dir + "fusion_remap_junction.unique.chr_seq_append.out",
			                    output_dir + "fusion_remap_junction.unique.chr_seq.extracted.repeat_filtered",
		                            chrom_blat)
		if do_annot_gene > 0:
		    if do_filter_fusion_by_repeat == 0:
			annot_genef(output_dir + "fusion_remap_junction.unique.chr_seq.extracted", 
			           filteredbest_dir + "best_remapped_junction2.txt", annot_gene_file, 
			           output_dir + "annotated.gene", logging_dir + "annot_gene.log")
		    else:
			annot_genef(output_dir + "fusion_remap_junction.unique.chr_seq.extracted.repeat_filtered", 
			           filteredbest_dir + "best_remapped_junction2.txt", annot_gene_file, 
			           output_dir + "annotated.gene", logging_dir + "annot_gene.log")
	##wig2bigwig(filteredbest_dir + "coverage.wig", filteredbest_dir + "coverage.bw", all_chromosomes_file)
        
	if rm_temp and os.path.exists(temp_dir):
	    shutil.rmtree(temp_dir, True)	    
        finish_time = datetime.now()
        duration = finish_time - start_time
	
        print >> sys.stderr
        print >> sys.stderr, "[%s] Finishing Mapsplice run (time used: %s)" % (right_now(), duration)
        print >> sys.stderr, "-----------------------------------------------" 
        
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        return 2


if __name__ == "__main__":
    sys.exit(main())