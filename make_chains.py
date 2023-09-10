#!/usr/bin/env python3
"""Make LASTZ chains master script."""
import argparse
import sys
import os
import subprocess
import shutil
import twobitreader
from constants import Constants
from modules.project_directory import OutputDirectoryManager
from modules.step_manager import StepManager
from modules.parameters import PipelineParameters
from modules.pipeline_steps import PipelineSteps
from modules.make_chains_logging import setup_logger
from modules.make_chains_logging import to_log
from modules.project_setup_procedures import setup_genome_sequences
from version import __version__

__author__ = "Bogdan Kirilenko, Michael Hiller, Virag Sharma, Ekaterina Osipova"
__maintainer__ = "Bogdan Kirilenko"
SCRIPT_LOCATION = os.path.abspath(os.path.dirname(__file__))
# TODO: setup proper logger


def parse_args():
    app = argparse.ArgumentParser(description=Constants.DESCRIPTION)
    app.add_argument(
        "target_name", help="Target genome identifier, e.g. hg38, human, etc."
    )
    app.add_argument(
        "query_name", help="Query genome identifier, e.g. mm10, mm39, mouse, etc."
    )
    app.add_argument(
        "target_genome", help="Target genome. Accepted formats are: fasta and 2bit."
    )
    app.add_argument(
        "query_genome", help="Query genome. Accepted formats are: fasta and 2bit."
    )
    app.add_argument("--project_dir", "--pd", help="Project directory. By default: pwd")

    app.add_argument(
        "--continue_from_step",
        help="Continue pipeline execution from this step",
        choices=PipelineSteps.ORDER,
        default=None,
    )

    app.add_argument(
        "--force",
        "-f",
        action="store_true",
        dest="force",
        help="Overwrite output directory if exists"
    )

    # Pipeline parameters group
    pipeline_params = app.add_argument_group('Pipeline Parameters')
    pipeline_params.add_argument("--lastz_y", default=Constants.DEFAULT_LASTZ_Y, type=int)
    pipeline_params.add_argument("--lastz_h", default=Constants.DEFAULT_LASTZ_H, type=int)
    pipeline_params.add_argument("--lastz_l", default=Constants.DEFAULT_LASTZ_L, type=int)
    pipeline_params.add_argument("--lastz_k", default=Constants.DEFAULT_LASTZ_K, type=int)
    pipeline_params.add_argument("--seq1_chunk", default=Constants.DEFAULT_SEQ1_CHUNK, type=int)
    pipeline_params.add_argument("--seq1_lap", default=0, type=int)
    pipeline_params.add_argument("--seq1_limit", default=4000, type=int)
    pipeline_params.add_argument("--seq2_chunk", default=Constants.DEFAULT_SEQ2_CHUNK, type=int)
    pipeline_params.add_argument("--seq2_lap", default=10000, type=int)
    pipeline_params.add_argument("--seq2_limit", default=10000, type=int)
    pipeline_params.add_argument("--fill_chain", default=1, type=int)
    pipeline_params.add_argument("--fill_unmask", default=1, type=int)
    pipeline_params.add_argument("--fill_chain_min_score", default=25000, type=int)
    pipeline_params.add_argument("--fill_insert_chain_minscore", default=5000, type=int)
    pipeline_params.add_argument("--fill_gap_max_size_t", default=20000, type=int)
    pipeline_params.add_argument("--fill_gap_max_size_q", default=20000, type=int)
    pipeline_params.add_argument("--fill_gap_min_size_t", default=30, type=int)
    pipeline_params.add_argument("--fill_gap_min_size_q", default=30, type=int)
    pipeline_params.add_argument("--fill_lastz_k", default=2000, type=int)
    pipeline_params.add_argument("--fill_lastz_l", default=3000, type=int)
    pipeline_params.add_argument("--fill_memory", default=15000, type=int)
    pipeline_params.add_argument("--fill_prepare_memory", default=50000, type=int)
    pipeline_params.add_argument("--chaining_queue", default="medium")
    pipeline_params.add_argument("--chaining_memory", default=50000, type=int)
    pipeline_params.add_argument("--clean_chain", default=1, type=int)
    pipeline_params.add_argument("--chain_clean_memory", default=100000, type=int)
    pipeline_params.add_argument("--clean_chain_parameters",
                                 default=Constants.DEFAULT_CLEAN_CHAIN_PARAMS)

    if len(sys.argv) < 5:
        app.print_help()
        sys.exit(1)

    args = app.parse_args()
    return args


class StepExecutables:
    def __init__(self):
        self.partition_script = self.__find_script("partitionSequence.pl")
        self.lastz_wrapper = self.__find_script("run_lastz.py")
        self.split_chain_into_random_parts = self.__find_script("split_chain_into_random_parts.pl")
        self.bundle_chrom_split_psl_files = self.__find_script("bundle_chrom_split_psl_files.perl")
        self.fa_to_two_bit = self.__find_binary("faToTwoBit")
        self.two_bit_to_fa = self.__find_binary("twoBitToFa")

    @staticmethod
    def __find_script(script_name):
        rel_path = os.path.join(SCRIPT_LOCATION, "standalone_scripts", script_name)
        abs_path = os.path.abspath(rel_path)
        if not os.path.isfile(abs_path):
            raise ValueError(f"Error! Cannot locate script: {script_name}")
        return abs_path

    @staticmethod
    def __find_binary(binary_name):
        binary_path = shutil.which(binary_name)
        if binary_path is None:
            raise ValueError(f"Error! Cannot locate binary: {binary_name}")
        return binary_path


def log_version():
    """Get git hash and current branch if possible."""
    cmd_hash = "git rev-parse HEAD"
    cmd_branch = "git rev-parse --abbrev-ref HEAD"
    try:
        git_hash = subprocess.check_output(
            cmd_hash, shell=True, cwd=SCRIPT_LOCATION
        ).decode("utf-8").strip()
        git_branch = subprocess.check_output(
            cmd_branch, shell=True, cwd=SCRIPT_LOCATION
        ).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        git_hash = "unknown"
        git_branch = "unknown"
    version = f"Version {__version__}\nCommit: {git_hash}\nBranch: {git_branch}\n"
    to_log("# Make Lastz Chains #")
    to_log(version)
    return version


def run_pipeline(args):
    # setup project dir, parameters and step manager
    project_dir = OutputDirectoryManager(args).project_dir
    step_manager = StepManager(project_dir, args)
    parameters = PipelineParameters(args)
    log_file = os.path.join(project_dir, "run.log")
    setup_logger(log_file)
    log_version()
    to_log(f"Making chains for {args.target_genome} and {args.query_genome} files, saving results to {project_dir}")

    # TODO: prepare input data
    parameters.dump_to_json(project_dir)
    step_executables = StepExecutables()
    # initiate input files
    target_chrom_rename_table = setup_genome_sequences(args.target_genome,
                                                       args.target_name,
                                                       project_dir,
                                                       step_executables)
    query_chrom_rename_table = setup_genome_sequences(args.query_genome,
                                                      args.query_name,
                                                      project_dir,
                                                      step_executables)
    # now execute steps
    step_manager.execute_steps(project_dir, parameters, step_executables)

    # check result?
    # TODO: implement this part


def main():
    args = parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
