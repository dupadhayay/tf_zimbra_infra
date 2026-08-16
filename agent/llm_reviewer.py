import json
import os

from openai import OpenAI


# ============================================================
# Azure OpenAI Configuration
# ============================================================

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]




client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/"
)


# ============================================================
# LLM Reviewer
# ============================================================

def review_terraform_plan(
    security_signals,
    retrieved_policies,
    resources,
    risk_score,
    risk_level
):

    policies_text = "\n\n".join(
        [
            f"""
Policy Title: {policy.get("title")}
Category: {policy.get("category")}

{policy.get("content")}
"""
            for policy in retrieved_policies
        ]
    )


    signals_text = json.dumps(
        security_signals,
        indent=2
    )


    resources_text = json.dumps(
        resources,
        indent=2
    )


    prompt = f"""
You are a Terraform Security Review Agent.

Your job is to review a Terraform plan against
company security and infrastructure policies.

Do NOT invent policies.

Use ONLY the provided policies and Terraform signals.

==================================================
CURRENT RISK INFORMATION
==================================================

Risk Score:
{risk_score}

Initial Risk Level:
{risk_level}


==================================================
SECURITY SIGNALS
==================================================

{signals_text}


==================================================
RETRIEVED COMPANY POLICIES
==================================================

{policies_text}


==================================================
TERRAFORM RESOURCES
==================================================

{resources_text}


==================================================
YOUR TASK
==================================================

Analyze the Terraform changes.

Identify:

1. Security violations
2. High-risk resources
3. Policy violations
4. Potential impact
5. Recommended remediation
6. Whether manual approval is required


Return ONLY valid JSON in this format:

{{
  "risk_level": "LOW | MEDIUM | HIGH",
  "manual_approval_required": true,
  "summary": "Short explanation",
  "violations": [
    {{
      "resource": "resource address",
      "severity": "LOW | MEDIUM | HIGH",
      "issue": "description",
      "policy": "policy title"
    }}
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ]
}}
"""


    response = client.chat.completions.create(

        model=AZURE_OPENAI_DEPLOYMENT,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior Terraform "
                    "DevSecOps security reviewer."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

    )


    content = response.choices[0].message.content


    # --------------------------------------------------------
    # Remove markdown JSON wrapper if model returns one
    # --------------------------------------------------------

    content = content.strip()

    if content.startswith("```json"):

        content = content.replace(
            "```json",
            "",
            1
        )

        content = content.rsplit(
            "```",
            1
        )[0]


    return json.loads(
        content.strip()
    )