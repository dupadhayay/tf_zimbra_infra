resource "azurerm_resource_group" "resourece" {
   for_each = var.rg
  name     = each.value.resource_group_name
  location = each.value.location
}

output "resource_group_names" {
  description = "Resource Group Names"

  value = {
    for key, rg in azurerm_resource_group.resourece :
    key => rg.name
  }
}