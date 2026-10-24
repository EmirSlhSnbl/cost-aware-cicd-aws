variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "project" {
  type    = string
  default = "finops-guard"
}

variable "owner" {
  description = "Owner tag value (your name or e-mail)."
  type        = string
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "allowed_cidrs" {
  description = "Who may reach the app."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "image_tag" {
  description = "Image tag to deploy."
  type        = string
  default     = "v1"
}

variable "desired_count" {
  description = "Running tasks. Keep 0 for the first apply, then set 1."
  type        = number
  default     = 0
}