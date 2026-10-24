variable "name" {
  type = string
}

variable "image_repository_url" {
  description = "ECR repository URL (without tag)."
  type        = string
}

variable "image_tag" {
  description = "Image tag to run."
  type        = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "app_port" {
  type    = number
  default = 8080
}

variable "cpu" {
  description = "Fargate CPU units (256 = 0.25 vCPU, the cheapest size)."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate memory in MiB (512 is the smallest valid for 256 CPU)."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of running tasks. 0 until the first image is pushed."
  type        = number
  default     = 0
}

variable "log_retention_days" {
  type    = number
  default = 7
}