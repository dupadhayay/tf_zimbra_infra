import os
import re
import json


class TerraformCodeAnalyzer:

    def __init__(self, terraform_root):
        self.terraform_root = terraform_root

    # ============================================================
    # Find Terraform files
    # ============================================================

    def find_tf_files(self):
        """
        Find all Terraform .tf files recursively.

        Ignores:
        - .terraform
        - .git
        """

        tf_files = []

        for root, dirs, files in os.walk(
            self.terraform_root
        ):

            dirs[:] = [
                d
                for d in dirs
                if d not in [
                    ".terraform",
                    ".git"
                ]
            ]

            for file in files:

                if file.endswith(".tf"):

                    tf_files.append(
                        os.path.join(
                            root,
                            file
                        )
                    )

        return sorted(tf_files)

    # ============================================================
    # Find tfvars files
    # ============================================================

    def find_tfvars_files(self):
        """
        Find all Terraform variable value files.

        Supports:
        - *.tfvars
        - *.auto.tfvars

        Ignores:
        - .terraform
        - .git
        """

        tfvars_files = []

        for root, dirs, files in os.walk(
            self.terraform_root
        ):

            dirs[:] = [
                d
                for d in dirs
                if d not in [
                    ".terraform",
                    ".git"
                ]
            ]

            for file in files:

                if (
                    file.endswith(".tfvars")
                    or file.endswith(".auto.tfvars")
                ):

                    tfvars_files.append(
                        os.path.join(
                            root,
                            file
                        )
                    )

        return sorted(tfvars_files)

    # ============================================================
    # Read file
    # ============================================================

    def read_file(self, file_path):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                return file.read()

        except Exception as error:

            return (
                f"ERROR reading "
                f"{file_path}: {error}"
            )

    # ============================================================
    # Remove Terraform comments
    # ============================================================

    def remove_full_line_comments(
        self,
        content
    ):
        """
        Remove full-line comments.

        Supports:
        # comment
        // comment
        """

        active_lines = []

        for line in content.splitlines():

            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            if stripped.startswith("//"):
                continue

            active_lines.append(line)

        return "\n".join(
            active_lines
        )

    # ============================================================
    # Detect Modules
    # ============================================================

    def detect_modules(
        self,
        content
    ):

        modules = []

        active_content = (
            self.remove_full_line_comments(
                content
            )
        )

        pattern = re.compile(
            r'module\s+"([^"]+)"\s*\{(.*?)\}',
            re.DOTALL
        )

        for match in pattern.finditer(
            active_content
        ):

            module_name = match.group(1)

            block = match.group(2)

            source_match = re.search(
                r'source\s*=\s*"([^"]+)"',
                block
            )

            source = (
                source_match.group(1)
                if source_match
                else None
            )

            modules.append(
                {
                    "name": module_name,
                    "source": source,
                    "status": "ACTIVE"
                }
            )

        return modules

    # ============================================================
    # Detect Resources
    # ============================================================

    def detect_resources(
        self,
        content
    ):

        resources = []

        active_content = (
            self.remove_full_line_comments(
                content
            )
        )

        pattern = re.compile(
            r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{',
            re.MULTILINE
        )

        for match in pattern.finditer(
            active_content
        ):

            resources.append(
                {
                    "type": match.group(1),
                    "name": match.group(2)
                }
            )

        return resources

    # ============================================================
    # Detect Data Sources
    # ============================================================

    def detect_data_sources(
        self,
        content
    ):

        data_sources = []

        active_content = (
            self.remove_full_line_comments(
                content
            )
        )

        pattern = re.compile(
            r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{',
            re.MULTILINE
        )

        for match in pattern.finditer(
            active_content
        ):

            data_sources.append(
                {
                    "type": match.group(1),
                    "name": match.group(2)
                }
            )

        return data_sources

    # ============================================================
    # Detect Variables
    # ============================================================

    def detect_variables(
        self,
        content
    ):

        variables = []

        active_content = (
            self.remove_full_line_comments(
                content
            )
        )

        pattern = re.compile(
            r'variable\s+"([^"]+)"\s*\{(.*?)\}',
            re.DOTALL
        )

        for match in pattern.finditer(
            active_content
        ):

            variable_name = match.group(1)

            block = match.group(2)

            type_match = re.search(
                r'type\s*=\s*(.+)',
                block
            )

            variable_type = (
                type_match.group(1).strip()
                if type_match
                else None
            )

            variables.append(
                {
                    "name": variable_name,
                    "type": variable_type
                }
            )

        return variables

    # ============================================================
    # Analyze Terraform files
    # ============================================================

    def analyze(self):

        result = {
            "terraform_root": self.terraform_root,
            "files": [],
            "modules": [],
            "resources": [],
            "data_sources": [],
            "variables": [],
            "tfvars_files": []
        }

        # --------------------------------------------------------
        # Terraform .tf files
        # --------------------------------------------------------

        tf_files = self.find_tf_files()

        for file_path in tf_files:

            content = self.read_file(
                file_path
            )

            relative_path = os.path.relpath(
                file_path,
                self.terraform_root
            )

            file_info = {
                "file": relative_path,
                "modules": self.detect_modules(
                    content
                ),
                "resources": self.detect_resources(
                    content
                ),
                "data_sources": self.detect_data_sources(
                    content
                ),
                "variables": self.detect_variables(
                    content
                ),
                "configuration": content
            }

            result["files"].append(
                file_info
            )

            # ----------------------------------------------------
            # Modules
            # ----------------------------------------------------

            for module in file_info[
                "modules"
            ]:

                result["modules"].append(
                    {
                        "file": relative_path,
                        **module
                    }
                )

            # ----------------------------------------------------
            # Resources
            # ----------------------------------------------------

            for resource in file_info[
                "resources"
            ]:

                result["resources"].append(
                    {
                        "file": relative_path,
                        **resource
                    }
                )

            # ----------------------------------------------------
            # Data sources
            # ----------------------------------------------------

            for data_source in file_info[
                "data_sources"
            ]:

                result["data_sources"].append(
                    {
                        "file": relative_path,
                        **data_source
                    }
                )

            # ----------------------------------------------------
            # Variables
            # ----------------------------------------------------

            for variable in file_info[
                "variables"
            ]:

                result["variables"].append(
                    {
                        "file": relative_path,
                        **variable
                    }
                )

        # --------------------------------------------------------
        # Terraform tfvars files
        # --------------------------------------------------------

        tfvars_files = (
            self.find_tfvars_files()
        )

        for file_path in tfvars_files:

            content = self.read_file(
                file_path
            )

            relative_path = os.path.relpath(
                file_path,
                self.terraform_root
            )

            result["tfvars_files"].append(
                {
                    "file": relative_path,
                    "configuration": content
                }
            )

        return result

    # ============================================================
    # Security Signals
    # ============================================================

    def security_signals(
        self,
        analysis
    ):

        signals = []

        for resource in analysis[
            "resources"
        ]:

            resource_type = resource[
                "type"
            ]

            if resource_type == (
                "azurerm_public_ip"
            ):

                signals.append(
                    {
                        "severity": "MEDIUM",
                        "signal": "PUBLIC_IP",
                        "resource": resource,
                        "reason": (
                            "Azure Public IP resource "
                            "detected. Review whether "
                            "public exposure is required."
                        )
                    }
                )

            if resource_type == (
                "azurerm_network_security_group"
            ):

                signals.append(
                    {
                        "severity": "HIGH",
                        "signal": "NETWORK_SECURITY_GROUP",
                        "resource": resource,
                        "reason": (
                            "Network Security Group "
                            "detected. Review inbound "
                            "rules for public exposure."
                        )
                    }
                )

            if resource_type == (
                "azurerm_key_vault"
            ):

                signals.append(
                    {
                        "severity": "MEDIUM",
                        "signal": "KEY_VAULT",
                        "resource": resource,
                        "reason": (
                            "Key Vault detected. "
                            "Review network access "
                            "and security configuration."
                        )
                    }
                )

            if resource_type == (
                "azurerm_storage_account"
            ):

                signals.append(
                    {
                        "severity": "MEDIUM",
                        "signal": "STORAGE_ACCOUNT",
                        "resource": resource,
                        "reason": (
                            "Storage Account detected. "
                            "Review public network "
                            "access and encryption."
                        )
                    }
                )

        return signals

    # ============================================================
    # Build Context
    # ============================================================

    def build_context(self):

        analysis = self.analyze()

        signals = self.security_signals(
            analysis
        )

        return {
            "terraform_analysis": analysis,
            "security_signals": signals
        }

    # ============================================================
    # Save Analysis
    # ============================================================

    def save_analysis(
        self,
        output_file
    ):

        context = self.build_context()

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                context,
                file,
                indent=2
            )

        return context