import json
import os
import sys

from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


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

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-10-21"
)


# ============================================================
# Load Terraform Plan
# ============================================================

def load_plan(plan_file):

    with open(plan_file, "r") as file:
        return json.load(file)


# ============================================================
# Extract Important Plan Information
# ============================================================

def summarize_plan(plan):

    resource_changes = plan.get(
        "resource_changes",
        []
    )

    creates = []
    updates = []
    destroys = []

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

        # --------------------------------------------
        # Create
        # --------------------------------------------

        if "create" in actions:

            creates.append(address)

        # --------------------------------------------
        # Update
        # --------------------------------------------

        if "update" in actions:

            updates.append(address)

        # --------------------------------------------
        # Destroy
        # --------------------------------------------

        if "delete" in actions:

            destroys.append(address)

        # --------------------------------------------
        # Public IP
        # --------------------------------------------

        if resource_type == "azurerm_public_ip":

            public_ips.append(address)

        # --------------------------------------------
        # NSG Rules
        # --------------------------------------------

        if resource_type == "azurerm_network_security_rule":

            source = after.get(
                "source_address_prefix"
            )

            port = after.get(
                "destination_port_range"
            )

            access = after.get(
                "access"
            )

            direction = after.get(
                "direction"
            )

            if (
                source in ["*", "0.0.0.0/0"]
                and access == "Allow"
                and direction == "Inbound"
            ):

                if port == "22":

                    public_ssh.append(address)

                if port == "3389":

                    public_rdp.append(address)

    return {
        "create_count": len(creates),
        "update_count": len(updates),
        "destroy_count": len(destroys),
        "creates": creates,
        "updates": updates,
        "destroys": destroys,
        "public_ip_count": len(public_ips),
        "public_ips": public_ips,
        "public_ssh": public_ssh,
        "public_rdp": public_rdp
    }


# ============================================================
# Retrieve RAG Policies
# ============================================================

def retrieve_policies(question):

    results = search_client.search(
        search_text=question,
        top=5
    )

    policies = []

    for result in results:

        policies.append({
            "title": result.get("title"),
            "category": result.get("category"),
            "content": result.get("content"),
            "score": result.get("@search.score")
        })

    return policies


# ============================================================
# Build AI Prompt
# ============================================================

def build_prompt(question, plan_summary, policies):

    return f"""
You are a Terraform Security Review Assistant.

You must answer the user's question using BOTH:

1. The actual Terraform plan information.
2. Company security policies retrieved from Azure AI Search.

Do not invent Terraform resources or security findings.

If the plan does not contain evidence of a security issue,
clearly say that the issue was not detected.

============================================================
USER QUESTION
============================================================

{question}


============================================================
ACTUAL TERRAFORM PLAN
============================================================

{json.dumps(plan_summary, indent=2)}


============================================================
COMPANY POLICIES
============================================================

{json.dumps(policies, indent=2)}


============================================================
INSTRUCTIONS
============================================================

Explain:

- What the Terraform plan is doing.
- Whether there are destroy operations.
- Whether public IPs are being created.
- Whether public SSH is detected.
- Whether public RDP is detected.
- Which company policies are relevant.
- What the risk is.
- Whether manual approval is recommended.

Keep the answer practical and concise.

Do not claim that a public IP automatically means
SSH/RDP is publicly exposed.

Use the actual plan evidence.
"""


# ============================================================
# Ask Azure OpenAI
# ============================================================

def ask_llm(prompt):

    response = client.chat.completions.create(

        model=AZURE_OPENAI_DEPLOYMENT,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Terraform and "
                    "Azure security reviewer."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# ============================================================
# Chat
# ============================================================

def chat(plan_file):

    plan = load_plan(plan_file)

    plan_summary = summarize_plan(plan)

    print("\nTerraform AI Reviewer")
    print("=====================")

    print("\nTerraform plan loaded:")
    print(
        f"Create : {plan_summary['create_count']}"
    )
    print(
        f"Update : {plan_summary['update_count']}"
    )
    print(
        f"Destroy: {plan_summary['destroy_count']}"
    )
    print(
        f"Public IP: {plan_summary['public_ip_count']}"
    )

    print("\nType 'exit' to quit.\n")

    while True:

        question = input("You: ").strip()

        if question.lower() == "exit":

            print("Goodbye!")
            break

        if not question:

            continue

        # --------------------------------------------
        # RAG Search
        # --------------------------------------------

        policies = retrieve_policies(
            question
        )

        # --------------------------------------------
        # Prompt
        # --------------------------------------------

        prompt = build_prompt(
            question,
            plan_summary,
            policies
        )

        # --------------------------------------------
        # LLM
        # --------------------------------------------

        answer = ask_llm(
            prompt
        )

        print("\nAI:")
        print(answer)
        print()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python3 agent/chatbot.py "
            "parent_module/tfplan.json"
        )

        sys.exit(1)

    plan_file = sys.argv[1]

    try:

        chat(plan_file)

    except FileNotFoundError:

        print(
            f"ERROR: Plan file not found: {plan_file}"
        )

        sys.exit(1)

    except Exception as error:

        print(
            f"ERROR: {error}"
        )

        sys.exit(1)