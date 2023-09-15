"""Class that holds paths to all necessary executables."""
import os
import shutil
from constants import Constants
from modules.error_classes import ExecutableNotFoundError
from modules.make_chains_logging import to_log


class StepExecutables:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.hl_kent_binaries_path = os.path.join(root_dir, Constants.KENT_BINARIES_DIRNAME)
        self.chain_clean_env_dir = os.path.join(root_dir, Constants.CHAIN_CLEAN_MICRO_ENV)
        self.not_found = []

        self.lastz_wrapper = self.__find_script(Constants.ScriptNames.RUN_LASTZ)
        self.repeat_filler = self.__find_script(Constants.ScriptNames.REPEAT_FILLER)

        self.fa_to_two_bit = self.__find_binary(Constants.ToolNames.FA_TO_TWO_BIT)
        self.two_bit_to_fa = self.__find_binary(Constants.ToolNames.TWO_BIT_TO_FA)
        self.psl_sort_acc = self.__find_binary(Constants.ToolNames.PSL_SORT_ACC)
        self.axt_chain = self.__find_binary(Constants.ToolNames.AXT_CHAIN)
        self.chain_anti_repeat = self.__find_binary(Constants.ToolNames.CHAIN_ANTI_REPEAT)
        self.chain_merge_sort = self.__find_binary(Constants.ToolNames.CHAIN_MERGE_SORT)
        self.chain_cleaner = self.__find_binary(Constants.ToolNames.CHAIN_CLEANER)
        self.chain_sort = self.__find_binary(Constants.ToolNames.CHAIN_SORT)
        self.chain_score = self.__find_binary(Constants.ToolNames.CHAIN_SCORE)
        self.lastz = self.__find_binary(Constants.ToolNames.LASTZ)
        self.chain_net = self.__locate_chain_net(Constants.ToolNames.CHAIN_NET)

        self.__check_completeness()

    def __find_script(self, script_name):
        rel_path = os.path.join(self.root_dir, "standalone_scripts", script_name)
        abs_path = os.path.abspath(rel_path)
        if not os.path.isfile(abs_path):
            self.not_found.append(script_name)
            return None
        return abs_path

    def __find_binary(self, binary_name):
        binary_path = shutil.which(binary_name)

        if binary_path is None:  # not in $PATH
            # Try to find it in the HL_kent_binaries directory
            binary_path = os.path.join(self.hl_kent_binaries_path, binary_name)

            if not os.path.exists(binary_path):
                self.not_found.append(binary_name)
        return binary_path

    def __locate_chain_net(self, chain_net):
        if shutil.which(chain_net):
            return True
        elif os.path.isfile(os.path.join(self.chain_clean_env_dir, chain_net)):
            return True
        self.not_found.append(chain_net)
        return None

    def __check_completeness(self):
        if len(self.not_found) == 0:
            to_log("All necessary executables found.")
            return
        not_found_bins = "\n".join([f"* {x}" for x in self.not_found])
        err_msg = (
            f"Error! The following tools not found neither in $PATH nor "
            f"in the download dir:\n{not_found_bins}\nPlease note that "
            f"chainNet should be placed either in $PATH or in the "
            f"{self.chain_clean_env_dir} directory. Other tools are "
            f"expected to be either in $PATH or {self.hl_kent_binaries_path}\n"
            f"Please use install_dependencies.py to automate the process."
        )
        raise ExecutableNotFoundError(err_msg)
