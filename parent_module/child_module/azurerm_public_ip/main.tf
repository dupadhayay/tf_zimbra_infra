data "azurerm_resource_group" "resourceData" {
    for_each =var.publicIP
  name = each.value.resource_group_name
}


resource "azurerm_public_ip" "public_ip" {
    for_each =var.publicIP
  name                = each.value.name
  resource_group_name = data.azurerm_resource_group.resourceData[each.key].name
  location            = data.azurerm_resource_group.resourceData[each.key].location
  allocation_method   = each.value.allocation_method
}

