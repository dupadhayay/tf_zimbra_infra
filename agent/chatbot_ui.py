import os
import sys

import streamlit as st


# ============================================================
# Allow importing existing chatbot functions
# ============================================================

sys.path.append(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


from chatbot import (
    load_plan,
    summarize_plan,
    retrieve_policies,
    build_prompt,
    ask_llm,
    build_terraform_context,
    generate_fix
)


# ============================================================
# Configuration
# ============================================================

PLAN_FILE = "parent_module/tfplan.json"
CODE_DIR = "parent_module"


# ============================================================
# Streamlit Page Configuration
# ============================================================

st.set_page_config(
    page_title="Terraform AI Security Reviewer",
    page_icon="🔐",
    layout="wide"
)


# ============================================================
# Application Header
# ============================================================

st.title(
    "🔐 Terraform AI Security Reviewer"
)

st.caption(
    "Terraform Code + Plan + Azure AI Search RAG + AI Reviewer"
)


# ============================================================
# Session State Initialization
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_question" not in st.session_state:
    st.session_state.last_question = None

if "last_policies" not in st.session_state:
    st.session_state.last_policies = []

if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

if "last_fix" not in st.session_state:
    st.session_state.last_fix = None


# ============================================================
# Load Terraform Plan
# ============================================================

try:

    plan = load_plan(
        PLAN_FILE
    )

    plan_summary = summarize_plan(
        plan
    )

except FileNotFoundError:

    st.error(
        f"❌ Terraform plan not found: {PLAN_FILE}"
    )

    st.stop()

except Exception as error:

    st.error(
        f"❌ Failed to load Terraform plan: {error}"
    )

    st.stop()


# ============================================================
# Build Terraform-Aware Context
# ============================================================

try:

    terraform_context = build_terraform_context(
        code_dir=CODE_DIR,
        plan_file=PLAN_FILE
    )

except Exception as error:

    st.error(
        f"❌ Terraform analysis failed: {error}"
    )

    st.stop()


# ============================================================
# Extract Analysis Results
# ============================================================

plan_context = terraform_context.get(
    "plan_context",
    {}
)

consistency = terraform_context.get(
    "consistency",
    {}
)

plan_counts = plan_context.get(
    "summary",
    {}
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header(
        "📊 Terraform Plan"
    )

    # --------------------------------------------------------
    # Plan Metrics
    # --------------------------------------------------------

    st.metric(
        "Create",
        plan_counts.get(
            "create_count",
            plan_summary.get(
                "create_count",
                0
            )
        )
    )

    st.metric(
        "Update",
        plan_counts.get(
            "update_count",
            plan_summary.get(
                "update_count",
                0
            )
        )
    )

    st.metric(
        "Delete",
        plan_counts.get(
            "delete_count",
            plan_summary.get(
                "destroy_count",
                0
            )
        )
    )

    st.metric(
        "Replace",
        plan_counts.get(
            "replace_count",
            0
        )
    )

    st.divider()

    # ========================================================
    # Security Signals
    # ========================================================

    st.subheader(
        "🔐 Security Signals"
    )

    # --------------------------------------------------------
    # Public IP
    # --------------------------------------------------------

    if plan_summary.get(
        "public_ips"
    ):

        st.warning(
            f"⚠️ "
            f"{plan_summary.get('public_ip_count', 0)} "
            "Public IP(s) detected"
        )

    else:

        st.success(
            "✅ No Public IP detected"
        )

    # --------------------------------------------------------
    # Public SSH
    # --------------------------------------------------------

    if plan_summary.get(
        "public_ssh"
    ):

        st.error(
            "🚨 Public SSH access detected"
        )

    else:

        st.success(
            "✅ No public SSH detected"
        )

    # --------------------------------------------------------
    # Public RDP
    # --------------------------------------------------------

    if plan_summary.get(
        "public_rdp"
    ):

        st.error(
            "🚨 Public RDP access detected"
        )

    else:

        st.success(
            "✅ No public RDP detected"
        )

    # ========================================================
    # Code / Plan Consistency
    # ========================================================

    st.divider()

    st.subheader(
        "🔄 Code / Plan Consistency"
    )

    inconsistency_count = consistency.get(
        "inconsistency_count",
        0
    )

    if inconsistency_count > 0:

        st.error(
            f"🚨 {inconsistency_count} "
            "inconsistency(s) detected"
        )

    else:

        st.success(
            "✅ Code and Plan appear consistent"
        )


# ============================================================
# Terraform Analysis Details
# ============================================================

with st.expander(
    "🔎 Terraform Analysis Details"
):

    st.write(
        "### Terraform Plan Summary"
    )

    st.json(
        plan_context.get(
            "summary",
            {}
        )
    )

    st.write(
        "### Code / Plan Consistency"
    )

    st.json(
        consistency
    )

    st.write(
        "### Security Signals"
    )

    st.json(
        terraform_context.get(
            "code_context",
            {}
        ).get(
            "security_signals",
            []
        )
    )


# ============================================================
# Previous Chat History
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# Chat Input
# ============================================================

question = st.chat_input(
    "Ask about your Terraform code, plan, risk or policies..."
)


# ============================================================
# Process New Question
# ============================================================

if question:

    # --------------------------------------------------------
    # Save Question
    # --------------------------------------------------------

    st.session_state.last_question = question

    # Clear previous fix
    st.session_state.last_fix = None

    # --------------------------------------------------------
    # Save User Message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    # --------------------------------------------------------
    # Display User Message
    # --------------------------------------------------------

    with st.chat_message(
        "user"
    ):

        st.markdown(
            question
        )

    # --------------------------------------------------------
    # AI Review
    # --------------------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        with st.spinner(
            "🔎 Analyzing Terraform code, plan and policies..."
        ):

            try:

                # =================================================
                # Retrieve RAG Policies
                # =================================================

                policies = retrieve_policies(
                    question
                )

                st.session_state.last_policies = policies

                # =================================================
                # Build Terraform-Aware Prompt
                # =================================================

                prompt = build_prompt(
                    question=question,
                    plan_summary=plan_summary,
                    policies=policies,
                    terraform_context=terraform_context
                )

                # =================================================
                # Ask Azure OpenAI
                # =================================================

                answer = ask_llm(
                    prompt
                )

                st.session_state.last_answer = answer

                # =================================================
                # Display Answer
                # =================================================

                st.markdown(
                    answer
                )

                # =================================================
                # Save Assistant Message
                # =================================================

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

            except Exception as error:

                st.error(
                    f"❌ AI review failed: {error}"
                )


# ============================================================
# Terraform Fix Section
# ============================================================

if st.session_state.last_question:

    st.divider()

    st.subheader(
        "🛠️ Terraform Remediation"
    )

    st.caption(
        "Generate an exact Terraform fix using the "
        "actual source code, tfvars, plan and policies."
    )

    # --------------------------------------------------------
    # Generate Fix Button
    # --------------------------------------------------------

    generate_fix_clicked = st.button(
        "🔧 Generate Terraform Fix",
        key="generate_terraform_fix",
        use_container_width=True
    )

    if generate_fix_clicked:

        with st.spinner(
            "🛠️ Generating Terraform remediation..."
        ):

            try:

                # =================================================
                # Build Dedicated Fix Question
                # =================================================

                fix_question = f"""
Generate an exact Terraform remediation for the
following Terraform security/review finding.

USER QUESTION:
{st.session_state.last_question}

Use the actual Terraform source code,
terraform.tfvars, Terraform plan,
consistency analysis and retrieved policies.

Do NOT invent:

- resources
- files
- variables
- module names
- resource names

Show:

1. Exact affected file
2. Exact resource
3. Current Terraform configuration
4. Current terraform.tfvars configuration
5. Exact recommended Terraform change
6. Expected terraform plan impact
7. Validation commands

Do not remove a Terraform module unless the
provided evidence proves that the module itself
is unnecessary.

Prefer the smallest possible change.
"""

                # =================================================
                # Generate Fix
                # =================================================

                fix = generate_fix(
                    question=fix_question,
                    plan_summary=plan_summary,
                    policies=st.session_state.last_policies,
                    terraform_context=terraform_context
                )

                # =================================================
                # Store Fix
                # =================================================

                st.session_state.last_fix = fix

            except Exception as error:

                st.error(
                    f"❌ Fix generation failed: {error}"
                )


# ============================================================
# Display Generated Fix
# ============================================================

if st.session_state.last_fix:

    st.divider()

    st.subheader(
        "🛠️ Recommended Terraform Fix"
    )

    st.markdown(
        st.session_state.last_fix
    )

    # --------------------------------------------------------
    # Validation Commands
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "✅ Recommended Validation"
    )

    st.code(
        """terraform fmt -recursive
terraform validate
terraform plan""",
        language="bash"
    )