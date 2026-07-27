variable "dataVnet" {
 type = map(object({
    name                = string
    address_space       = list(string)
    resource_group_name = string
  }))
} 
