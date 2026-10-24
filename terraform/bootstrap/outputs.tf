output "state_bucket" {
  description = "Put this in terraform/envs/dev/backend.tf."
  value       = aws_s3_bucket.state.id
}

output "plan_role_arn" {
  description = "Role for pull_request workflows (Week 3)."
  value       = aws_iam_role.plan.arn
}

output "apply_role_arn" {
  description = "Role for main-branch deploy workflow (Week 5)."
  value       = aws_iam_role.apply.arn
}