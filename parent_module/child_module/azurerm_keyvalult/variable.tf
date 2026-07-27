variable "keyvault" {
  type = object({
    name                       = string
    location                   = string
    resource_group_name        = string
    rbac_authorization_enabled = bool
    sku_name                   = string
    soft_delete_retention_days = number

  })
}
