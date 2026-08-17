import os
import uuid

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
api_key = os.environ["AZURE_SEARCH_API_KEY"]

index_name = "terraform-policies"

credential = AzureKeyCredential(api_key)

client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential
)


documents = [
    {
        "id": str(uuid.uuid4()),
        "title": "Security Policy",
        "category": "security",
        "content": """
Production resources must never expose SSH port 22
directly to the public internet.

The following configuration is HIGH RISK:

source_address_prefix = "*"
destination_port_range = "22"
access = "Allow"

Production NSG rules allowing SSH from the internet
require manual security approval.

Production resources must never expose RDP port 3389
directly to the public internet.
"""
    },

    {
        "id": str(uuid.uuid4()),
        "title": "Terraform Infrastructure Policy",
        "category": "terraform",
        "content": """
All production infrastructure must be managed through Terraform.

Terraform destroy operations against production resources
require manual approval.

Any Terraform plan containing destructive changes must be
reviewed before apply.

Production resources must have appropriate Environment tags.

Required tags:

Environment
Owner
CostCenter
ManagedBy
"""
    },

    {
        "id": str(uuid.uuid4()),
        "title": "Azure Naming Convention",
        "category": "naming",
        "content": """
Azure Resource Groups must follow this naming pattern:

rg-<application>-<environment>

Examples:

rg-zimbra-prod
rg-zimbra-dev
rg-payment-prod

Production resources must use the prod environment suffix.
Development resources must use the dev environment suffix.
"""
    },

    {
        "id": str(uuid.uuid4()),
        "title": "Incident Postmortem 001",
        "category": "incident",
        "content": """
An NSG rule was accidentally deployed with:

source_address_prefix = "*"
destination_port_range = "22"

This exposed SSH access to the internet.

The incident resulted in an emergency security review.

Terraform plans must be reviewed for:

Public SSH access
Public RDP access
Open NSG rules
Production network changes

Any such change should receive HIGH RISK classification.
"""
    }
]


result = client.upload_documents(documents=documents)

for item in result:
    print(item)