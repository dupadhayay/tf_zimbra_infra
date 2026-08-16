variable "rg" {
  type = map(object({
    resource_group_name = string
    location            = string
  }))
}
