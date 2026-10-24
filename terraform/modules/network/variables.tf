variable "name" {
  description = "Name prefix for resources."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "app_port" {
  description = "Port the container listens on."
  type        = number
  default     = 8080
}

variable "allowed_cidrs" {
  description = "CIDR blocks allowed to reach the app port."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}