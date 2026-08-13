module "resource" {
  source = "./child_module/azurerm_resource"
  rg     = var.rg
}
output "rg_names" {
  value = module.resource.resource_group_names
}

# module "keyVault" {
#   depends_on = [module.resource]
#   source     = "./child_module/azurerm_keyvalult"
#   keyvault   = var.keyvault
# }

module "public_ip" {
  depends_on = [module.resource]
  source     = "./child_module/azurerm_public_ip"
  publicIP   = var.publicIP
}

module "vnet" {
  depends_on = [module.resource]
  source     = "./child_module/azurerm_virtual_network"
  vnets    = var.vnets
}

module "subnet" {
  depends_on  = [module.vnet, module.resource]
  source      = "./child_module/azurerm_subnet"
  subnetsData = var.subnetsData
}

# module "VM" {
#   depends_on = [module.resource, module.public_ip, module.subnet, module.vnet]

#   source = "./child_module/azurerm_virtual_machine"
#   VM     = var.vms
# }
