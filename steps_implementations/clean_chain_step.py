"""Clean chains step."""
import os
import shutil
import subprocess
import platform
from modules.make_chains_logging import to_log
from modules.parameters import PipelineParameters
from modules.project_paths import ProjectPaths
from modules.step_executables import StepExecutables
from modules.error_classes import PipelineSubprocessError


def do_chains_clean(params: PipelineParameters,
                    project_paths: ProjectPaths,
                    executables: StepExecutables):
    # select input chain files, depending on whether fill chains step was executed or not
    if params.fill_chain is True:
        to_log(f"Chains were filled: using {project_paths.filled_chain} as input")
        input_chain = project_paths.filled_chain
    else:
        to_log(f"Fill chains step was skipped: using {project_paths.merged_chain} as input")
        input_chain = project_paths.merged_chain

    if not os.path.isfile(input_chain):
        raise RuntimeError(f"Cannot find {input_chain}")

    shutil.move(input_chain, project_paths.before_cleaning_chain)
    to_log(f"Chain to be cleaned saved to: {project_paths.before_cleaning_chain}")
    # TODO: I don't really like this original decision, to be revised
    _output_chain = input_chain.removesuffix(".gz")
    _clean_chain_args = params.clean_chain_parameters.split()
    # dirty hack to override chainNet not found error
    _temp_env = os.environ.copy()
    _temp_env["PATH"] = f"{project_paths.chain_clean_micro_env}:" + _temp_env["PATH"]

    chain_cleaner_cmd = [
        executables.chain_cleaner,
        project_paths.before_cleaning_chain,
        params.seq_1_dir,
        params.seq_2_dir,
        _output_chain,
        project_paths.clean_removed_suspects,
        f"-linearGap={params.chain_linear_gap}",
        f"-tSizes={params.seq_1_len}",
        f"-qSizes={params.seq_2_len}",
        *_clean_chain_args,
    ]

    to_log("Executing the following chain cleaner command:")
    to_log(" ".join(chain_cleaner_cmd))

    with open(project_paths.chain_cleaner_log, 'w') as f:
        process = subprocess.Popen(chain_cleaner_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=_temp_env,
                                   text=True)
        stdout, stderr = process.communicate()

        # Write stdout to log file and also capture it in a variable
        f.write(stdout)
        # Couldn't open /proc/self/stat , No such file or directory
        # error on macOS. If this error -> ignore, but crash in case of anything else.
        if process.returncode != 0:  # handle error
            is_macos = platform.system() == "Darwin"
            if is_macos:
                # on macOS, it always crashes...
                to_log(
                    "Chain cleaner returned non-zero error code."
                    "However, you run macOS, where it always return non-zero code."
                    "It is impossible to differentiate whether it's a true error or now."
                )
                pass
            else:
                # here, proper handling
                error_message = f"chain cleaner process died with the following error message: {stderr}"
                raise PipelineSubprocessError(error_message)

    to_log(f"Chain clean results saved to: {_output_chain}")

    gzip_cmd = ["gzip", _output_chain]
    try:
        subprocess.check_call(gzip_cmd)
    except subprocess.CalledProcessError:
        raise PipelineSubprocessError("gzip command at clean chain step failed")

    to_log("Chain clean DONE")
