data "azurerm_client_config" "config" {
}


resource "azurerm_key_vault" "keyVault" {
  
  name                       = var.keyvault.name
  location                   = var.keyvault.location
  resource_group_name        = var.keyvault.resource_group_name
  rbac_authorization_enabled = var.keyvault.rbac_authorization_enabled
  tenant_id                  = data.azurerm_client_config.config.tenant_id
  sku_name                   = var.keyvault.sku_name
  soft_delete_retention_days = var.keyvault.soft_delete_retention_days

  access_policy {
    tenant_id = data.azurerm_client_config.config.tenant_id
    object_id = data.azurerm_client_config.config.object_id

    key_permissions = [
      "Create",
      "Get",
    ]

    secret_permissions = [
      "Set",
      "Get",
      "Delete",
      "Purge",
      "Recover",
      "List"
    ]
  }
}

# data "azurerm_key_vault" "keyvaultData" {
#   name                = var.keyvault.name
#   resource_group_name = var.keyvault.resource_group_name
# }


# resource "azurerm_key_vault_secret" "name" {
#   name         = var.keyvault.admin_username
#   value        = var.keyvault.admin_user_Name
#   key_vault_id = data.azurerm_key_vault.keyvaultData.id
# }

# resource "azurerm_key_vault_secret" "password" {
#   name         = var.keyvault.admin_password_name
#   value        = var.keyvault.admin_password
#   key_vault_id = data.azurerm_key_vault.keyvaultData.id
# }

