vnets = {
  vn1 = {
    name                = "frontend-vnet"
    address_space       = ["10.0.0.0/16"]
    resource_group_name = "rg_deepak"
  }
  vn2 = {
    name                = "backend-vnet"
    address_space       = ["10.1.0.0/16"]
    resource_group_name = "rg_dhundu"
  }
}


vms = {
  VM1 = {
    name                = "nic_card1"
    resource_group_name = "rg_deepak"
    vnet_name           = "frontend-vnet"
    subnet_name         = "frontend-subnet"
    ip_configuration = {
      name                          = "internal"
      private_ip_address_allocation = "Dynamic"
    }
    vmname                          = "adminvm2"
    caching                         = "ReadWrite"
    storage_account_type            = "Standard_LRS"
    publisher                       = "Canonical"
    offer                           = "ubuntu-24_04-lts"
    sku                             = "server"
    version                         = "latest"
    disable_password_authentication = false

    size = "Standard_D2s_v3"
    admin_username = "adminusername"
    admin_password_secret_name = "adminpassword"
    pipname      = "public-ip1"
    keyvaultname = "KeyvaultVMPassword"



  }
  VM2 = {
    name                = "nic_card2"
    resource_group_name = "rg_dhundu"
    vnet_name           = "backend-vnet"
    subnet_name         = "backend-subnet"
    ip_configuration = {
      name                          = "internal"
      private_ip_address_allocation = "Dynamic"
    }
    vmname               = "adminvm1"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"

    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"

    size = "Standard_D2s_v3"
    admin_username = "adminusername"
    admin_password_secret_name = "adminpassword"
    disable_password_authentication = false
    pipname                         = "public-ip2"
    keyvaultname                    = "KeyvaultVMPassword"


  }
}

subnets = {
  subnet1 = {
    resource_group_name  = "rg_deepak"
    virtual_network_name = "frontend-vnet"
    address_prefixes     = ["10.0.1.0/24"]
    name                 = "frontend-subnet"
  }

  subnet2 = {
    resource_group_name  = "rg_dhundu"
    virtual_network_name = "backend-vnet"
    address_prefixes     = ["10.1.1.0/24"]
    name                 = "backend-subnet"
  }
}

rgs = {
  rg1 = {
    resource_group_name = "rg_deepak"
    location            = "Central India"
  }
  rg2 = {
    resource_group_name = "rg_dhundu"
    location            = "Central India"

  }
   rg23= {
    resource_group_name = "rg_rondu"
    location            = "Central India"

  }
}

publicIPs = {
  publicIP1 = {
    name                = "public-ip1"
    resource_group_name = "rg_deepak"
    location            = "Central India"
    allocation_method   = "Static"
  }
  PublicIP2 = {
    name                = "public-ip2"
    resource_group_name = "rg_dhundu"
    location            = "Central India"
    allocation_method   = "Static"

  }
}

keyvault = {
  name                       = "KeyvaultVMPassword"
  location                   = "Central India"
  resource_group_name        = "rg_deepak"
  rbac_authorization_enabled = false
  sku_name                   = "premium"
  soft_delete_retention_days = 7
   
}
