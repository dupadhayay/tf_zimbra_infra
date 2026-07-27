variable "VM" {
  type = map(object({
    name                = string
    resource_group_name = string

    vnet_name   = string
    subnet_name = string

   ip_configuration = object({
      name                          = string
      private_ip_address_allocation = string
    })
    size                            = string
    admin_username                  = string
   admin_password_secret_name                  = string
    disable_password_authentication = bool
    caching                         = string
    storage_account_type            = string
    publisher                       = string
    offer                           = string
    sku                             = string
    version                         = string
    pipname                         = string
    keyvaultname                    = string
    })
  )
}
