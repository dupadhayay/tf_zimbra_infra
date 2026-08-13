import json
import os
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from llm_reviewer import review_terraform_plan


# ============================================================
# Azure AI Search Configuration
# ============================================================

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
SEARCH_INDEX = "terraform-policies"

credential = AzureKeyCredential(
    SEARCH_API_KEY
)

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=credential
)


# ============================================================
# Security Signal Detection
# ============================================================

def detect_security_signals(resource_changes):

    signals = []

    for resource in resource_changes:

        resource_type = resource.get(
            "type",
            ""
        )

        address = resource.get(
            "address",
            ""
        )

        change = resource.get(
            "change",
            {}
        )

        after = change.get(
            "after"
        ) or {}

        actions = change.get(
            "actions",
            []
        )

        # ----------------------------------------------------
        # Public IP Detection
        # ----------------------------------------------------

        if resource_type == "azurerm_public_ip":

            allocation_method = after.get(
                "allocation_method"
            )

            if allocation_method:

                signals.append({
                    "type": "PUBLIC_IP",
                    "resource": address,
                    "severity": "MEDIUM",
                    "reason": "Public IP resource detected"
                })

        # ----------------------------------------------------
        # NSG Rule Detection
        # ----------------------------------------------------

        if resource_type == "azurerm_network_security_rule":

            source = after.get(
                "source_address_prefix"
            )

            destination_port = after.get(
                "destination_port_range"
            )

            access = after.get(
                "access"
            )

            direction = after.get(
                "direction"
            )

            # ------------------------------------------------
            # Public SSH
            # ------------------------------------------------

            if (
                source in ["*", "0.0.0.0/0"]
                and access == "Allow"
                and direction == "Inbound"
                and destination_port == "22"
            ):

                signals.append({
                    "type": "PUBLIC_SSH",
                    "resource": address,
                    "severity": "HIGH",
                    "reason": (
                        "SSH port 22 exposed "
                        "to the public internet"
                    )
                })

            # ------------------------------------------------
            # Public RDP
            # ------------------------------------------------

            if (
                source in ["*", "0.0.0.0/0"]
                and access == "Allow"
                and direction == "Inbound"
                and destination_port == "3389"
            ):

                signals.append({
                    "type": "PUBLIC_RDP",
                    "resource": address,
                    "severity": "HIGH",
                    "reason": (
                        "RDP port 3389 exposed "
                        "to the public internet"
                    )
                })

        # ----------------------------------------------------
        # Terraform Destroy Detection
        # ----------------------------------------------------

        if "delete" in actions:

            signals.append({
                "type": "DESTROY",
                "resource": address,
                "severity": "HIGH",
                "reason": (
                    "Terraform resource "
                    "will be destroyed"
                )
            })

    return signals


# ============================================================
# Terraform Plan Analysis
# ============================================================

def analyze_plan(plan_file):

    # --------------------------------------------------------
    # Load Terraform Plan JSON
    # --------------------------------------------------------

    with open(
        plan_file,
        "r"
    ) as file:

        plan = json.load(file)

    resource_changes = plan.get(
        "resource_changes",
        []
    )

    # ========================================================
    # Security Signal Detection
    # ========================================================

    security_signals = detect_security_signals(
        resource_changes
    )

    # ========================================================
    # Resource Counters
    # ========================================================

    destroy_count = 0
    create_count = 0
    update_count = 0

    resources = []

    for resource in resource_changes:

        address = resource.get(
            "address",
            ""
        )

        change = resource.get(
            "change",
            {}
        )

        actions = change.get(
            "actions",
            []
        )

        # ----------------------------------------------------
        # Store resource information
        # ----------------------------------------------------

        resources.append({
            "address": address,
            "actions": actions
        })

        # ----------------------------------------------------
        # Count actual changes
        #
        # READ actions are ignored.
        # ----------------------------------------------------

        if "delete" in actions:

            destroy_count += 1

        if "create" in actions:

            create_count += 1

        if "update" in actions:

            update_count += 1

    # ========================================================
    # Generate RAG Search Query
    # ========================================================

    search_query_parts = []

    # --------------------------------------------------------
    # Terraform Change Signals
    # --------------------------------------------------------

    if destroy_count > 0:

        search_query_parts.append(
            "Terraform destroy production resources "
            "manual approval"
        )

    if create_count > 0:

        search_query_parts.append(
            "Terraform infrastructure creation "
            "security policy"
        )

    if update_count > 0:

        search_query_parts.append(
            "Terraform infrastructure modification "
            "security policy"
        )

    # ========================================================
    # Security Signal Types
    # ========================================================

    signal_types = {
        signal["type"]
        for signal in security_signals
    }

    # --------------------------------------------------------
    # Public SSH
    # --------------------------------------------------------

    if "PUBLIC_SSH" in signal_types:

        search_query_parts.append(
            "production public SSH NSG "
            "port 22 security policy"
        )

    # --------------------------------------------------------
    # Public RDP
    # --------------------------------------------------------

    if "PUBLIC_RDP" in signal_types:

        search_query_parts.append(
            "production public RDP NSG "
            "port 3389 security policy"
        )

    # --------------------------------------------------------
    # Public IP
    # --------------------------------------------------------

    if "PUBLIC_IP" in signal_types:

        search_query_parts.append(
            "Azure public IP security "
            "exposure policy"
        )

    # --------------------------------------------------------
    # Destroy
    # --------------------------------------------------------

    if "DESTROY" in signal_types:

        search_query_parts.append(
            "Terraform resource destruction "
            "production approval policy"
        )

    # --------------------------------------------------------
    # Default Query
    # --------------------------------------------------------

    if not search_query_parts:

        search_query_parts.append(
            "Terraform infrastructure "
            "security policy"
        )

    # --------------------------------------------------------
    # Remove Duplicate Queries
    # --------------------------------------------------------

    search_query_parts = list(
        dict.fromkeys(
            search_query_parts
        )
    )

    # --------------------------------------------------------
    # Final RAG Query
    # --------------------------------------------------------

    search_query = " ".join(
        search_query_parts
    )

    # ========================================================
    # Retrieve Policies from Azure AI Search
    # ========================================================

    results = search_client.search(
        search_text=search_query,
        top=3
    )

    policies = []

    for result in results:

        policies.append({

            "title": result.get(
                "title"
            ),

            "category": result.get(
                "category"
            ),

            "score": result.get(
                "@search.score"
            ),

            "content": result.get(
                "content"
            )
        })

    # ========================================================
    # Risk Score
    # ========================================================

    risk_score = 0

    # --------------------------------------------------------
    # Terraform Destroy
    # --------------------------------------------------------

    if destroy_count > 0:

        risk_score += 60

    # --------------------------------------------------------
    # Large Creation
    # --------------------------------------------------------

    if create_count > 50:

        risk_score += 10

    # --------------------------------------------------------
    # Large Update
    # --------------------------------------------------------

    if update_count > 20:

        risk_score += 10

    # ========================================================
    # Security Signals
    # ========================================================

    # Public SSH = HIGH
    if "PUBLIC_SSH" in signal_types:

        risk_score += 70

    # Public RDP = HIGH
    if "PUBLIC_RDP" in signal_types:

        risk_score += 70

    # Destroy is already scored above.
    if "DESTROY" in signal_types:

        risk_score = max(
            risk_score,
            60
        )

    # Public IP = MEDIUM
    if "PUBLIC_IP" in signal_types:

        risk_score += 20

    # --------------------------------------------------------
    # Maximum Score = 100
    # --------------------------------------------------------

    risk_score = min(
        risk_score,
        100
    )

    # ========================================================
    # Risk Level
    # ========================================================

    if risk_score >= 70:

        risk_level = "HIGH"

    elif risk_score >= 30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    # ========================================================
    # Approval Decision
    # ========================================================

    if risk_level == "HIGH":

        decision = "MANUAL_APPROVAL"

    elif risk_level == "MEDIUM":

        decision = "REVIEW_RECOMMENDED"

    else:

        decision = "AUTO_PROCEED"

    # ========================================================
    # LLM Review
    # ========================================================

    llm_review = review_terraform_plan(

        security_signals=security_signals,

        retrieved_policies=policies,

        resources=resources,

        risk_score=risk_score,

        risk_level=risk_level
    )

    # ========================================================
    # Final Result
    # ========================================================

    result = {

        "risk_score": risk_score,

        "risk_level": risk_level,

        "decision": decision,

        "destroy_count": destroy_count,

        "create_count": create_count,

        "update_count": update_count,

        "search_query": search_query,

        "security_signals": security_signals,

        "retrieved_policies": policies,

        "llm_review": llm_review,

        "resources": resources
    }

    return result


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Validate Arguments
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print(
            "Usage: python3 agent.py <tfplan.json>"
        )

        sys.exit(1)

    plan_file = sys.argv[1]

    # --------------------------------------------------------
    # Execute Agent
    # --------------------------------------------------------

    try:

        result = analyze_plan(
            plan_file
        )

        print(
            json.dumps(
                result,
                indent=2
            )
        )

    except FileNotFoundError:

        print(
            f"ERROR: Terraform plan file not found: "
            f"{plan_file}"
        )

        sys.exit(1)

    except json.JSONDecodeError:

        print(
            f"ERROR: Invalid JSON file: "
            f"{plan_file}"
        )

        sys.exit(1)

    except KeyError as error:

        print(
            f"ERROR: Required environment variable "
            f"missing: {error}"
        )

        sys.exit(1)

    except Exception as error:

        print(
            f"ERROR: {error}"
        )

        sys.exit(1)