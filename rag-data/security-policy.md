# Security Policy

## Public SSH Access

Production resources must never expose SSH port 22
directly to the public internet.

The following configuration is considered HIGH RISK:

source_address_prefix = "*"
destination_port_range = "22"
access = "Allow"

Production NSG rules allowing SSH from the internet
require manual security approval.

## Public RDP Access

Production resources must never expose RDP port 3389
directly to the public internet.

Any NSG rule allowing:

source_address_prefix = "*"
destination_port_range = "3389"

must be classified as HIGH RISK.