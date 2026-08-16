import re


class TerraformConsistencyAnalyzer:

    def __init__(
        self,
        code_context,
        plan_context
    ):
        self.code_context = code_context
        self.plan_context = plan_context

    # ============================================================
    # Code Resource Types
    # ============================================================

    def get_code_resource_types(self):

        resources = (
            self.code_context
            .get("terraform_analysis", {})
            .get("resources", [])
        )

        return {
            resource.get("type")
            for resource in resources
            if resource.get("type")
        }

    # ============================================================
    # Active Code Modules
    # ============================================================

    def get_code_modules(self):

        modules = (
            self.code_context
            .get("terraform_analysis", {})
            .get("modules", [])
        )

        return {
            module.get("name")
            for module in modules
            if (
                module.get("name")
                and module.get("status", "ACTIVE")
                == "ACTIVE"
            )
        }

    # ============================================================
    # Plan Resources
    # ============================================================

    def get_plan_resources(self):

        resources = []

        for key in [
            "creates",
            "updates",
            "deletes",
            "replaces"
        ]:

            resources.extend(
                self.plan_context.get(
                    key,
                    []
                )
            )

        return resources

    # ============================================================
    # Extract Module From Address
    # ============================================================

    def extract_module_name(
        self,
        address
    ):

        match = re.match(
            r"module\.([^.]+)",
            address
        )

        if match:

            return match.group(1)

        return None

    # ============================================================
    # Analyze
    # ============================================================

    def analyze(self):

        code_resource_types = (
            self.get_code_resource_types()
        )

        code_modules = (
            self.get_code_modules()
        )

        plan_resources = (
            self.get_plan_resources()
        )

        resources_checked = []
        inconsistencies = []

        for resource in plan_resources:

            address = resource.get(
                "address",
                ""
            )

            resource_type = resource.get(
                "type"
            )

            module_name = (
                self.extract_module_name(
                    address
                )
            )

            issues = []

            # ----------------------------------------------------
            # Check module
            # ----------------------------------------------------

            if (
                module_name
                and module_name not in code_modules
            ):

                issues.append(
                    f"Plan references module "
                    f"'{module_name}', but the module "
                    f"is not active in the current "
                    f"Terraform source."
                )

            # ----------------------------------------------------
            # Check resource type
            # ----------------------------------------------------

            if (
                resource_type
                and resource_type
                not in code_resource_types
            ):

                issues.append(
                    f"Plan contains resource type "
                    f"'{resource_type}', but this "
                    f"resource type was not detected "
                    f"in the current Terraform source."
                )

            result = {
                "address": address,
                "type": resource_type,
                "module": module_name,
                "issues": issues
            }

            resources_checked.append(
                result
            )

            # ----------------------------------------------------
            # Store inconsistencies
            # ----------------------------------------------------

            if issues:

                inconsistencies.append(
                    result
                )

        return {
            "total_plan_resources": len(
                resources_checked
            ),

            "code_resource_types": sorted(
                code_resource_types
            ),

            "code_modules": sorted(
                code_modules
            ),

            "inconsistency_count": len(
                inconsistencies
            ),

            "inconsistencies": inconsistencies,

            "resources_checked": resources_checked
        }