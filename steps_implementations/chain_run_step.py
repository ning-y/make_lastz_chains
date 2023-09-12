"""Do Chain Run."""
import os
import shutil
import subprocess
from parallelization.nextflow_wrapper import NextflowWrapper
from constants import Constants
from steps_implementations.chain_run_bundle_substep import bundle_chrom_split_psl_files


def psl_bundle(cat_out_dirname, chain_run_dir, psl_sort_acc, params):
    # 1.1 -> sort
    # TODO: potentially danger part here: can exceed the bash limit for number of arguments
    concatenated_files = [os.path.join(cat_out_dirname, x) for x in os.listdir(cat_out_dirname)]
    file_list_arg = " ".join(concatenated_files)

    psl_sort_temp_dir = os.path.join(chain_run_dir, Constants.PSL_SORT_TEMP_DIRNAME)
    os.makedirs(psl_sort_temp_dir, exist_ok=True)
    sorted_psl_dir = os.path.join(chain_run_dir, Constants.SORTED_PSL_DIRNAME)
    os.makedirs(sorted_psl_dir, exist_ok=True)
    sort_cmd = [psl_sort_acc, "nohead", sorted_psl_dir, psl_sort_temp_dir, file_list_arg]
    subprocess.call(sort_cmd)
    shutil.rmtree(psl_sort_temp_dir)
    # 1.2 -> bundle chrom split files
    split_psl_dir = os.path.join(chain_run_dir, Constants.SPLIT_PSL_DIRNAME)
    os.makedirs(split_psl_dir, exist_ok=True)
    bundle_chrom_split_psl_files(sorted_psl_dir, params.seq_1_len, split_psl_dir, Constants.BUNDLE_PSL_MAX_BASES)


def make_chains_joblist(chain_run_dir, params, executables):
    # Prepare parameters
    seq1_dir = params.seq_1_dir
    seq2_dir = params.seq_2_dir
    # TODO: deal with matrix
    # matrix = params.lastz_q if params.lastz_q else ""
    # matrix = ""
    min_score = params.chain_min_score
    linear_gap = params.chain_linear_gap

    chain_out_dir = os.path.join(chain_run_dir, Constants.CHAIN_RUN_OUT_DIRNAME)
    os.makedirs(chain_out_dir, exist_ok=True)

    split_psl_dir = os.path.join(chain_run_dir, Constants.SPLIT_PSL_DIRNAME)
    bundle_filenames = os.listdir(split_psl_dir)

    cluster_jobs = []
    for bundle_filename in bundle_filenames:
        in_path = os.path.join(split_psl_dir, bundle_filename)
        out_path = os.path.join(chain_out_dir, f"{bundle_filename}.chain")
        cmd = [executables.axt_chain,
               "-psl",
               "-verbose=0",
               f"-minScore={min_score}",
               f"-linearGap={linear_gap}",
               in_path,
               seq1_dir,
               seq2_dir,
               "stdout",
               "|",
               executables.chain_anti_repeat,
               seq1_dir,
               seq2_dir,
               "stdin",
               out_path]
        cluster_jobs.append(" ".join(cmd))
    return cluster_jobs


def do_chain_run(project_dir, params, executables):
    # Setup directories
    cat_out_dirname = os.path.join(project_dir, Constants.TEMP_CAT_DIRNAME)
    chain_run_dir = os.path.join(project_dir, Constants.TEMP_AXT_CHAIN_DIRNAME)
    os.makedirs(chain_run_dir, exist_ok=True)

    # Part 1: make bundles
    psl_bundle(cat_out_dirname, chain_run_dir, executables.psl_sort_acc, params)

    # Part 2: create chains joblist
    chain_jobs = make_chains_joblist(chain_run_dir, params, executables)

    # Part 3: execute cluster jobs
    joblist_path = os.path.join(chain_run_dir, Constants.CHAIN_JOBLIST_FILENAME)
    with open(joblist_path, "w") as f:
        f.write("\n".join(chain_jobs))
    nextflow_manager = NextflowWrapper()
    nextflow_manager.execute(joblist_path,
                             Constants.NextflowConstants.LASTZ_CONFIG_PATH,
                             chain_run_dir,
                             wait=True)
    nextflow_manager.cleanup()
