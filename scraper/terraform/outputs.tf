output "ecr_push_role_arn" {
  description = "ARN to set as the AWS_ECR_PUSH_ROLE_ARN GitHub Actions repository variable"
  value       = aws_iam_role.ecr_push.arn
}
