import json


class TerraformPlanAnalyzer:

    def __init__(self, plan_file):
        self.plan_file = plan_file

    def load_plan(self):
        with open(self.plan_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def analyze(self):

        plan = self.load_plan()

        resource_changes = plan.get(
            "resource_changes", []
        )

        creates = []
        updates = []
        deletes = []
        replaces = []

        for resource in resource_changes:

            address = resource.get("address")

            change = resource.get(
                "change", {}
            )

            actions = change.get(
                "actions", []
            )

            item = {
                "address": address,
                "type": resource.get("type"),
                "name": resource.get("name"),
                "actions": actions
            }

            if actions == ["create"]:
                creates.append(item)

            elif actions == ["update"]:
                updates.append(item)

            elif actions == ["delete"]:
                deletes.append(item)

            elif "delete" in actions and "create" in actions:
                replaces.append(item)

        return {
            "summary": {
                "create_count": len(creates),
                "update_count": len(updates),
                "delete_count": len(deletes),
                "replace_count": len(replaces)
            },
            "creates": creates,
            "updates": updates,
            "deletes": deletes,
            "replaces": replaces
        }