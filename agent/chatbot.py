import json
import os

from openai import OpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from code_analyzer import TerraformCodeAnalyzer
from plan_analyzer import TerraformPlanAnalyzer
from consistency_analyzer import TerraformConsistencyAnalyzer


# ============================================================
# Configuration
# ============================================================

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
SEARCH_INDEX = "terraform-policies"

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# ============================================================
# Azure AI Search
# ============================================================

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_API_KEY)
)


# ============================================================
# Azure OpenAI
# ============================================================

client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/"
)


# ============================================================
# Terraform Code + Plan Context
# ============================================================

def build_terraform_context(
    code_dir="./parent_module",
    plan_file="./parent_module/tfplan.json"
):
    """
    Build complete Terraform-aware context.

    Includes:
    - Terraform source code analysis
    - Terraform plan analysis
    - Code / Plan consistency analysis
    """

    code_analyzer = TerraformCodeAnalyzer(code_dir)
    plan_analyzer = TerraformPlanAnalyzer(plan_file)

    code_context = code_analyzer.build_context()
    plan_context = plan_analyzer.analyze()

    consistency = TerraformConsistencyAnalyzer(
        code_context,
        plan_context
    ).analyze()

    return {
        "code_context": code_context,
        "plan_context": plan_context,
        "consistency": consistency
    }


# ============================================================
# Load Terraform Plan
# ============================================================

def load_plan(plan_file):
    """
    Load terraform show -json output.
    """

    with open(
        plan_file,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# Terraform Security Signals
# ============================================================

def summarize_plan(plan):
    """
    Extract high-level Terraform and security signals.
    """

    resource_changes = plan.get(
        "resource_changes",
        []
    )

    creates = []
    updates = []
    destroys = []
    replaces = []

    public_ips = []
    public_ssh = []
    public_rdp = []

    for resource in resource_changes:

        address = resource.get(
            "address",
            ""
        )

        resource_type = resource.get(
            "type",
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

        after = change.get(
            "after"
        ) or {}

        # ----------------------------------------------------
        # Terraform changes
        # ----------------------------------------------------

        if "create" in actions:
            creates.append(address)

        if "update" in actions:
            updates.append(address)

        if "delete" in actions:
            destroys.append(address)

        if set(actions) == {"delete", "create"}:
            replaces.append(address)

        # ----------------------------------------------------
        # Public IP
        # ----------------------------------------------------

        if resource_type == "azurerm_public_ip":
            public_ips.append(address)

        # ----------------------------------------------------
        # Network Security Rules
        # ----------------------------------------------------

        if resource_type == "azurerm_network_security_rule":

            source = after.get(
                "source_address_prefix"
            )

            source_prefixes = after.get(
                "source_address_prefixes"
            ) or []

            port = after.get(
                "destination_port_range"
            )

            port_ranges = after.get(
                "destination_port_ranges"
            ) or []

            access = after.get(
                "access"
            )

            direction = after.get(
                "direction"
            )

            public_source = (
                source in ["*", "0.0.0.0/0"]
                or "*" in source_prefixes
                or "0.0.0.0/0" in source_prefixes
            )

            inbound_allow = (
                public_source
                and access == "Allow"
                and direction == "Inbound"
            )

            if inbound_allow:

                if (
                    port == "22"
                    or "22" in port_ranges
                ):
                    public_ssh.append(address)

                if (
                    port == "3389"
                    or "3389" in port_ranges
                ):
                    public_rdp.append(address)

    return {
        "create_count": len(creates),
        "update_count": len(updates),
        "destroy_count": len(destroys),
        "replace_count": len(replaces),
        "creates": creates,
        "updates": updates,
        "destroys": destroys,
        "replaces": replaces,
        "public_ip_count": len(public_ips),
        "public_ips": public_ips,
        "public_ssh": public_ssh,
        "public_rdp": public_rdp
    }


# ============================================================
# RAG Policy Retrieval
# ============================================================

def retrieve_policies(question):
    """
    Retrieve relevant company policies from Azure AI Search.
    """

    results = search_client.search(
        search_text=question,
        top=5
    )

    policies = []

    for result in results:

        policies.append(
            {
                "title": result.get("title"),
                "category": result.get("category"),
                "content": result.get("content"),
                "score": result.get("@search.score")
            }
        )

    return policies


# ============================================================
# Terraform Source Extraction
# ============================================================

def extract_source_files(code_context):
    """
    Extract source files and detected resources/modules
    from TerraformCodeAnalyzer output.

    This gives the LLM explicit evidence about files
    that actually exist.
    """

    analysis = code_context.get(
        "terraform_analysis",
        {}
    )

    files = analysis.get(
        "files",
        []
    )

    return files


# ============================================================
# Build Terraform-Aware Review Prompt
# ============================================================

def build_prompt(
    question,
    plan_summary,
    policies,
    terraform_context=None
):
    """
    Build the main Terraform AI review prompt.
    """

    context_text = ""

    if terraform_context:

        code_context = terraform_context.get(
            "code_context",
            {}
        )

        plan_context = terraform_context.get(
            "plan_context",
            {}
        )

        consistency = terraform_context.get(
            "consistency",
            {}
        )

        source_files = extract_source_files(
            code_context
        )

        context_text = f"""
============================================================
TERRAFORM SOURCE CODE ANALYSIS
============================================================

{json.dumps(
    code_context,
    indent=2
)}

============================================================
ACTUAL TERRAFORM SOURCE FILES
============================================================

{json.dumps(
    source_files,
    indent=2
)}

============================================================
TERRAFORM PLAN ANALYSIS
============================================================

{json.dumps(
    plan_context,
    indent=2
)}

============================================================
CODE / PLAN CONSISTENCY
============================================================

{json.dumps(
    consistency,
    indent=2
)}
"""

    return f"""
You are a senior Terraform DevSecOps AI Reviewer.

You analyze REAL Terraform source code,
REAL Terraform plan data and
REAL company security policies.

Your most important requirement is:

NEVER INVENT TERRAFORM EVIDENCE.

Use ONLY the evidence supplied in this prompt.

============================================================
USER QUESTION
============================================================

{question}

============================================================
TERRAFORM PLAN SUMMARY
============================================================

{json.dumps(
    plan_summary,
    indent=2
)}

{context_text}

============================================================
COMPANY POLICIES FROM RAG
============================================================

{json.dumps(
    policies,
    indent=2
)}

============================================================
STRICT REVIEW RULES
============================================================

1. Analyze the actual Terraform source code.

2. Analyze the actual Terraform plan.

3. Identify CREATE, UPDATE, DELETE and REPLACE operations.

4. Identify security-sensitive resources.

5. Public IP does NOT automatically mean SSH exposure.

6. Public IP does NOT automatically mean RDP exposure.

7. Only report SSH/RDP exposure when actual evidence exists.

8. Check Code / Plan consistency.

9. Use ONLY retrieved company policies for policy violations.

10. Use exact Terraform file paths from the source evidence.

11. Use exact Terraform resource names from the source evidence.

12. Never invent a Terraform file.

13. Never invent a Terraform resource.

14. Never invent an existing variable.

15. Never invent an NSG or firewall rule.

16. Never invent a policy.

17. If evidence is insufficient, explicitly say:

Evidence insufficient to confirm.

18. Recommendations must preserve the existing Terraform architecture.

19. Prefer minimal Terraform changes.

20. Never recommend deleting a resource unless evidence
    clearly shows that the resource is unnecessary or
    explicitly requested by the user.

============================================================
TAGGING RULE
============================================================

Do NOT assume a tagging violation simply because tags are
not visible in one resource.

Check the actual Terraform source.

If required tag variables are not present:

Evidence insufficient to confirm equivalent tagging elsewhere.

Do not invent variables such as:

environment
owner
costcenter

unless they actually exist in the supplied Terraform code.

============================================================
FIX RECOMMENDATION
============================================================

For every confirmed finding provide:

Finding:
<what is wrong>

Affected File:
<exact file path>

Resource:
<exact Terraform resource>

Current Configuration:
<actual configuration from source>

Recommended Fix:
<minimal Terraform change>

Reason:
<technical reason>

Policy Impact:
<policy evidence>

If a safe fix cannot be generated:

Recommended Fix:
Insufficient evidence to safely generate an exact Terraform fix.

============================================================
ANSWER FORMAT
============================================================

Risk Level:
LOW / MEDIUM / HIGH

Summary:
<short explanation>

Findings:

1. <finding>

Affected File:
<exact file>

Resource:
<exact resource>

Current Configuration:
<actual code>

Recommended Fix:
<exact Terraform recommendation>

Reason:
<technical explanation>

Policy Impact:
- <policy>
- <impact>

Approval:
AUTO_PROCEED / MANUAL_REVIEW
"""


# ============================================================
# Generate Terraform Fix
# ============================================================

def generate_fix(
    question,
    plan_summary,
    policies,
    terraform_context
):
    """
    Generate a safe, code-aware Terraform remediation.

    Important:
    This function DOES NOT modify Terraform files.
    It only generates a remediation recommendation.
    """

    code_context = terraform_context.get(
        "code_context",
        {}
    )

    plan_context = terraform_context.get(
        "plan_context",
        {}
    )

    consistency = terraform_context.get(
        "consistency",
        {}
    )

    source_files = extract_source_files(
        code_context
    )

    fix_prompt = f"""
You are a senior Terraform DevSecOps remediation engineer.

Generate a SAFE, MINIMAL and CODE-AWARE Terraform remediation.

Use ONLY the Terraform source code, Terraform plan,
consistency analysis and retrieved company policies
provided below.

Do not use assumptions as facts.

============================================================
USER REQUEST
============================================================

{question}

============================================================
TERRAFORM SOURCE CODE
============================================================

{json.dumps(
    code_context,
    indent=2
)}

============================================================
ACTUAL SOURCE FILES
============================================================

{json.dumps(
    source_files,
    indent=2
)}

============================================================
TERRAFORM PLAN
============================================================

{json.dumps(
    plan_context,
    indent=2
)}

============================================================
PLAN SUMMARY
============================================================

{json.dumps(
    plan_summary,
    indent=2
)}

============================================================
CODE / PLAN CONSISTENCY
============================================================

{json.dumps(
    consistency,
    indent=2
)}

============================================================
COMPANY POLICIES
============================================================

{json.dumps(
    policies,
    indent=2
)}

============================================================
STRICT REMEDIATION RULES
============================================================

1. Only modify Terraform code supported by evidence.

2. Never invent a Terraform resource.

3. Never invent an existing variable.

4. If a new variable is required, explicitly write:

   NEW VARIABLE REQUIRED

5. Never invent a file path.

6. Never invent a resource name.

7. Never invent a module.

8. Never claim SSH/RDP exposure without actual evidence.

9. Do not remove resources blindly.

10. Preserve the existing Terraform architecture.

11. Prefer the smallest possible change.

12. Identify the exact Terraform file.

13. Identify the exact Terraform resource.

14. Show the actual relevant existing configuration.

15. Show the exact recommended configuration.

16. Do not use placeholder variables as if they already exist.

17. If the recommendation requires a variable that does
    not exist, clearly identify it as NEW.

18. Explain why the change is required.

19. Explain expected Terraform plan impact.

20. Provide validation commands.

21. Do NOT automatically assume that a Public IP must be
    deleted. First determine whether the source evidence
    proves that it is unnecessary.

22. If the only evidence is that a Public IP exists and
    there is no evidence of SSH/RDP exposure, state:

    Public IP detected, but direct management exposure
    is not confirmed.

23. If a fix cannot be safely determined from the evidence,
    say:

    Insufficient evidence to safely generate an exact
    Terraform fix.

============================================================
SPECIAL RULE FOR CURRENT CODE
============================================================

The CURRENT CODE section must contain ONLY code that
actually exists in the supplied Terraform source.

Do not reconstruct or invent missing code.

If exact code is not available:

CURRENT CODE:
Exact configuration not available in analyzer evidence.

============================================================
SPECIAL RULE FOR FILE PATH
============================================================

The AFFECTED FILE must be one of the files listed in:

ACTUAL SOURCE FILES

Never invent a path.

============================================================
SPECIAL RULE FOR VARIABLES
============================================================

Before recommending:

var.environment
var.owner
var.costcenter
var.tags

verify that the variable exists in the supplied source.

If it does not exist:

NEW VARIABLE REQUIRED

Do NOT pretend it already exists.

============================================================
OUTPUT FORMAT
============================================================

FIX SUMMARY:
<short explanation>

AFFECTED FILE:
<exact existing Terraform file path>

RESOURCE:
<exact Terraform resource address/type>

CURRENT CODE:
<actual relevant Terraform configuration>

RECOMMENDED CHANGE:
<exact Terraform code change>

CHANGES REQUIRED:
1. <specific change>
2. <specific change>

WHY:
<technical explanation>

EXPECTED IMPACT:
<what terraform plan is expected to do after the change>

RISK AFTER FIX:
LOW / MEDIUM / HIGH

VALIDATION:
terraform fmt -recursive
terraform validate
terraform plan

APPROVAL:
AUTO_PROCEED / MANUAL_REVIEW
"""

    return ask_llm(
        fix_prompt
    )


# ============================================================
# Azure OpenAI
# ============================================================

def ask_llm(prompt):
    """
    Send prompt to Azure OpenAI.
    """

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior Terraform "
                    "DevSecOps engineer and "
                    "infrastructure security reviewer. "
                    "Use ONLY supplied Terraform evidence. "
                    "Never invent Terraform files, "
                    "resources or variables."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content