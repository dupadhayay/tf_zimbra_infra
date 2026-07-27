data "azurerm_resource_group" "resourceData" {
  for_each = var.VM
  name     = each.value.resource_group_name
}

data "azurerm_subnet" "subnetData" {
  for_each             = var.VM
  name                 = each.value.subnet_name
  virtual_network_name = each.value.vnet_name
  resource_group_name  = each.value.resource_group_name
}

data "azurerm_key_vault" "keyvaultDatas" {
  name                = var.VM["VM1"].keyvaultname
  resource_group_name = var.VM["VM1"].resource_group_name
}

data "azurerm_key_vault_secret" "secretValue" {
  for_each = var.VM
  name         = each.value.admin_username
  key_vault_id = data.azurerm_key_vault.keyvaultDatas.id
}

data "azurerm_key_vault_secret" "password" {
  for_each = var.VM
  name         = each.value.admin_password_secret_name
  key_vault_id = data.azurerm_key_vault.keyvaultDatas.id
}



resource "azurerm_network_interface" "NIC" {
  for_each            = var.VM
  name                = each.value.name
  location            = data.azurerm_resource_group.resourceData[each.key].location
  resource_group_name = data.azurerm_resource_group.resourceData[each.key].name
  

  ip_configuration {
    name                          = each.value.ip_configuration.name
    subnet_id                     = data.azurerm_subnet.subnetData[each.key].id
    private_ip_address_allocation = each.value.ip_configuration.private_ip_address_allocation
    public_ip_address_id = data.azurerm_public_ip.publicIp[each.key].id
  }
}
data "azurerm_public_ip" "publicIp" {
  for_each             = var.VM
  name                = each.value.pipname
  resource_group_name = each.value.resource_group_name
}


resource "azurerm_linux_virtual_machine" "VMLinux" {
  for_each                        = var.VM
  name                            = each.key
  resource_group_name             = each.value.resource_group_name
  location                        = data.azurerm_resource_group.resourceData[each.key].location
  size                            = each.value.size
  admin_username                  = data.azurerm_key_vault_secret.secretValue[each.key].value
  admin_password                  = data.azurerm_key_vault_secret.password[each.key].value
  disable_password_authentication = each.value.disable_password_authentication
  network_interface_ids = [
    azurerm_network_interface.NIC[each.key].id
  ]
  os_disk {
    caching              = each.value.caching
    storage_account_type = each.value.storage_account_type
  }

  source_image_reference {
    publisher = each.value.publisher
    offer     = each.value.offer
    sku       = each.value.sku
    version   = each.value.version
  }
}
