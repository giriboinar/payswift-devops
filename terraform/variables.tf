variable "region" {
  description = "AWS region for the (not applied) design"
  type        = string
  default     = "ap-south-1"
}

variable "db_username" {
  description = "RDS master username (design only)"
  type        = string
  default     = "payswift"
}

variable "db_password" {
  description = "RDS master password — pass via TF_VAR_db_password, never commit it"
  type        = string
  sensitive   = true
}
