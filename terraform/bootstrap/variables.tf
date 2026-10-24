variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "eu-central-1"
}

variable "project" {
  description = "Short project name, used as a prefix and as the Project tag."
  type        = string
  default     = "finops-guard"
}

variable "owner" {
  description = "Owner tag value (your name or e-mail)."
  type        = string
}

variable "github_owner" {
  description = "GitHub user or organisation that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name."
  type        = string
  default     = "cost-aware-cicd-aws"
}

variable "github_owner_id" {
  description = "Numeric GitHub user/org ID (appears in the OIDC sub claim)."
  type        = string
}

variable "github_repo_id" {
  description = "Numeric GitHub repository ID (appears in the OIDC sub claim)."
  type        = string
}