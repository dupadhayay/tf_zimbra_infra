
import json
import os

from openai import OpenAI


# ============================================================
# Azure OpenAI Configuration
# ============================================================

AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].strip()
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"].strip()
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"].strip()


# ============================================================
# Azure OpenAI v1 Client
# ============================================================

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

    # --------------------------------------------------------
    # Prepare Policies
    # --------------------------------------------------------

    policies_text = "\n\n".join(
        [
            f"""
Policy Title: {policy.get("title")}

Category: {policy.get("category")}

Content:
{policy.get("content")}
"""
            for policy in retrieved_policies
        ]
    )

    # --------------------------------------------------------
    # Prepare Security Signals
    # --------------------------------------------------------

    signals_text = json.dumps(
        security_signals,
        indent=2
    )

    # --------------------------------------------------------
    # Prepare Terraform Resources
    # --------------------------------------------------------

    resources_text = json.dumps(
        resources,
        indent=2
    )

    # ========================================================
    # Prompt
    # ========================================================

    prompt = f"""
You are a Terraform Security Review Agent.

Your job is to review a Terraform plan against
company security and infrastructure policies.

IMPORTANT RULES:

- Do NOT invent policies.
- Use ONLY the provided company policies.
- Use ONLY the provided Terraform security signals.
- Do NOT assume policies that are not provided.
- Return ONLY valid JSON.
- Do not return Markdown.
- Do not wrap the JSON in ```json.

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


==================================================
REQUIRED JSON FORMAT
==================================================

{{
  "risk_level": "LOW",
  "manual_approval_required": false,
  "summary": "Short explanation",
  "violations": [
    {{
      "resource": "resource address",
      "severity": "LOW",
      "issue": "description",
      "policy": "policy title"
    }}
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ]
}}

Allowed risk levels:

LOW
MEDIUM
HIGH

Allowed severity values:

LOW
MEDIUM
HIGH
"""

    # ========================================================
    # OpenAI Request
    # ========================================================

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Terraform security review agent. "
                    "Return only valid JSON."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_completion_tokens=1000,
    )

    # ========================================================
    # Extract Response
    # ========================================================

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Azure OpenAI returned an empty response."
        )

    content = content.strip()

    # ========================================================
    # Remove Markdown JSON Wrapper
    # ========================================================

    if content.startswith("```json"):

        content = content[len("```json"):].strip()

        if content.endswith("```"):
            content = content[:-3].strip()

    elif content.startswith("```"):

        content = content[3:].strip()

        if content.endswith("```"):
            content = content[:-3].strip()

    # ========================================================
    # Parse JSON
    # ========================================================

    try:

        return json.loads(content)

    except json.JSONDecodeError as error:

        print("==========================================")
        print("LLM INVALID JSON RESPONSE")
        print("==========================================")
        print(content)
        print("==========================================")

        raise RuntimeError(
            f"Azure OpenAI returned invalid JSON: {error}"
        ) from error
````
