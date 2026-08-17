# Terraform Infrastructure Policy

All production infrastructure must be managed through
Terraform.

Terraform destroy operations against production
resources require manual approval.

Any Terraform plan containing destructive changes must
be reviewed before apply.

Production resources must have appropriate Environment
tags.

Required tags:

Environment
Owner
CostCenter
ManagedBy