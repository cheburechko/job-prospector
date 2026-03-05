terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.28"
    }
  }

  backend "s3" {
    bucket       = "aws-is-the-best-terraform-state"
    key          = "job-prospector/proxy/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
  }
}
