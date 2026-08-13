# Incident Postmortem 001

## Public NSG Exposure

An NSG rule was accidentally deployed with:

source_address_prefix = "*"
destination_port_range = "22"

This exposed SSH access to the internet.

The incident resulted in an emergency security review.

## Prevention

Terraform plans must be reviewed for:

- Public SSH access
- Public RDP access
- Open NSG rules
- Production network changes

Any such change should receive HIGH RISK classification.