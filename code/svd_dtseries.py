'''
svd_dtseries.py

For each subject-run in the specified partition: 
    - gets preprocessed dense timeseries 
    - centers it
    - computes svd 
    - saves to .mat

Tim Farrell, tmf@bu.edu
20160219
'''
import argparse
import scipy.io as scio
import dask.array as da
from os import environ, listdir
from hcp_analysis_utils import *

# parse args
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,\
                                 description=\
                  "\nFor each subject-run pair for this partition (i.e. sge_task_id):" +\
                  "\n\t- gets preprocessed dense timeseries" +\
                  "\n\t- centers it" +\
                  "\n\t- computes svd" +\
                  "\n\t- saves to .mat") 
parser.add_argument('sge_task_id', nargs=1, type=int, help="SGE_TASK_ID from qsub.") 
parser.add_argument('--save-plots', dest='save_plots', action='store_const',\
                    const=True, default=False,\
                    help="To save preprocessing plots, when preprocessing the timeseries." +\
                         " False by default.") 
parser.add_argument('--allow-recomputing', dest='allow_recomputing', action='store_const',\
                    const=True, default=False,\
                    help="To compute all svds, even if subject-run svd already in $HCP/data/svds." +\
                         " False by default.") 
parser.add_argument('--noise-size-limit', dest='noise_size_limit', nargs=1, type=int,\
                    help="To limit the size of the noise mask. No limit by default.", default=[None])
args = parser.parse_args() 

# get subject-runs of this partition (i.e. sge_task_id) 
project_datadir = '/projectnb/bohland/HCP/data/'
f = open(project_datadir + 'id_partitions.txt', 'r')
subjects = [l.strip().split('\t') for l in f.readlines()][args.sge_task_id[0] - 1]
f.close()
subject_runs = [(s, r) for s in subjects\
                       for r in ['REST1_LR','REST1_RL','REST2_LR','REST2_RL']]

# get those subject-runs for which svds were already computed
subject_runs_w_svd = [(s0, s1) for (s0, s1, _) in \
                      [svd.split('-') for svd in listdir(project_datadir + 'svds/')]] 

# compute svd for subject-runs, if not done already  
for subject_run in subject_runs: 
    if (not subject_run in subject_runs_w_svd) or args.allow_recomputing: 
        subject, run = subject_run 
        print("Getting preprocessed dts for " + subject + '-' + run + "...") 
        # get preprocessed doubly centered matrix
        try: 
            ppts = get_preprocessed_ts(subject, run, save_plots=args.save_plots,\
                                           noise_size_limit=args.noise_size_limit[0])
        except: 
            print("There was an error obtaining the timeseries for " + " ".join([subject, run])\
                  + ".\nThis run probably does not exist for this subject.")
            continue
        print("Centering...") 
        M = doubly_center_c(ppts)
        print("Computing SVD...") 
        # compute SVD
        [U, S, V] = [op.compute() for op in da.linalg.svd(\
                     da.from_array(M, chunks=(4000, 1200)))]
        print("Saving .mat...") 
        # save result to .mat 
        scio.savemat(project_datadir + 'svds/' + subject + '-' + run + '-svd.mat',\
			 dict(zip(['U', 'S', 'V'], [U, S, V])))
        print("Done " + subject + '-' + run + ".")
    else: 
        print("The svd for " + str(subject_run) + " is in $HCP/data/svds.\nPass --allow-recomputing " +\
              " to recompute.")
