data "azurerm_resource_group" "resourceData" {
  for_each = var.dataVnet
  name = each.value.resource_group_name 
}


resource "azurerm_virtual_network" "vnet" {
  for_each = var.dataVnet

  name                = each.value.name
  address_space       = each.value.address_space
  location            = data.azurerm_resource_group.resourceData[each.key].location
  resource_group_name = data.azurerm_resource_group.resourceData[each.key].name
}
