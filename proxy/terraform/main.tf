provider "aws" {
  region = local.region
}

data "aws_availability_zones" "available" {
  # Exclude local zones
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  region = "eu-central-1"
  name   = "simple-proxy"
  # target_group_name = local.name

  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)

  # container_name = "simple-proxy"
  # container_port = 3000
  # https_port     = 443

  tags = {
    name = local.name
  }

  # secret_arn_prefix     = "arn:aws:secretsmanager:eu-central-1:894608133151:secret"
  # secret_ssl_cert       = "${local.secret_arn_prefix}:prod/proxy/ssl/cert-GT92t4"
  # secret_ssl_cert_chain = "${local.secret_arn_prefix}:prod/proxy/ssl/cert-chain-kXogL4"
  # secret_ssl_key        = "${local.secret_arn_prefix}:prod/proxy/ssl/key-MQGLq7"
  # secret_creds          = "${local.secret_arn_prefix}:proxy/creds-C2zEWe"
  # secret_creds_username = "${resource.aws_secretsmanager_secret.creds.arn}:username:AWSCURRENT:${resource.aws_secretsmanager_secret_version.creds.version_id}"
  # secret_creds_password = "${resource.aws_secretsmanager_secret.creds.arn}:password:AWSCURRENT:${resource.aws_secretsmanager_secret_version.creds.version_id}"

  # route53_zone_id = "Z09770033CPYEFANHENOP"
}

################################################################################
# Cluster
################################################################################

# module "ecs" {
#   source  = "terraform-aws-modules/ecs/aws"
#   version = "7.3.1"

#   cluster_name = local.name

#   # Cluster capacity providers
#   cluster_capacity_providers = ["FARGATE_SPOT"]
#   default_capacity_provider_strategy = {
#     FARGATE_SPOT = {
#       weight = 100
#     }
#   }

#   services = {
#     simple-proxy = {
#       assign_public_ip = true
#       cpu              = 512
#       memory           = 1024

#       autoscaling_min_capacity = 1
#       autoscaling_max_capacity = 4

#       # Container definition(s)
#       container_definitions = {
#         (local.container_name) = {
#           cpu       = 512
#           memory    = 1024
#           essential = true
#           image     = "894608133151.dkr.ecr.eu-central-1.amazonaws.com/job-prospector/simple-proxy:latest"

#           readonlyRootFilesystem = false

#           healthCheck = {
#             command = ["CMD-SHELL", "nc -vz localhost ${local.container_port} || exit 1"]
#           }

#           environment = [
#             {
#               name  = "PORT"
#               value = local.container_port
#             }
#           ]

#           secrets = [
#             {
#               name      = "CERT_BLOB"
#               valueFrom = local.secret_ssl_cert
#             },
#             {
#               name      = "CERT_CHAIN_BLOB"
#               valueFrom = local.secret_ssl_cert_chain
#             },
#             {
#               name      = "KEY_BLOB"
#               valueFrom = local.secret_ssl_key
#             },
#             {
#               name      = "USERNAME"
#               valueFrom = local.secret_creds_username
#             },
#             {
#               name      = "PASSWORD"
#               valueFrom = local.secret_creds_password
#             }
#           ]

#           portMappings = [
#             {
#               name          = local.container_name
#               containerPort = local.container_port
#               hostPort      = local.container_port
#               protocol      = "tcp"
#             }
#           ]

#           memoryReservation = 100

#           restartPolicy = {
#             enabled              = true
#             restartAttemptPeriod = 60
#           }
#         }
#       }

#       deployment_configuration = {
#         strategy = "ROLLING"
#       }

#       load_balancer = {
#         service = {
#           target_group_arn = module.nlb.target_groups[local.target_group_name].arn
#           container_name   = local.container_name
#           container_port   = local.container_port
#         }
#       }

#       task_exec_secret_arns = [
#         local.secret_ssl_cert,
#         local.secret_ssl_cert_chain,
#         local.secret_ssl_key,
#         resource.aws_secretsmanager_secret.creds.arn,
#       ]

#       subnet_ids                    = module.vpc.public_subnets
#       vpc_id                        = module.vpc.vpc_id
#       availability_zone_rebalancing = "ENABLED"
#       security_group_ingress_rules = {
#         nlb = {
#           from_port                    = local.container_port
#           to_port                      = local.container_port
#           description                  = "Service port"
#           referenced_security_group_id = module.nlb.security_group_id
#           ip_protocol                  = "tcp"
#         }
#         vpc_https = {
#           description = "VPC https"
#           ip_protocol = "tcp"
#           cidr_ipv4   = module.vpc.vpc_cidr_block
#           from_port   = local.https_port
#           to_port     = local.https_port
#         }
#       }
#       security_group_egress_rules = {
#         all = {
#           cidr_ipv4   = "0.0.0.0/0"
#           ip_protocol = "-1"
#         }
#       }
#     }
#   }

#   tags = local.tags
# }

################################################################################
# Supporting Resources
################################################################################

# module "nlb" {
#   source  = "terraform-aws-modules/alb/aws"
#   version = "~> 10.0"

#   name = local.name

#   load_balancer_type = "network"

#   vpc_id  = module.vpc.vpc_id
#   subnets = module.vpc.public_subnets

#   # Security Group
#   security_group_ingress_rules = {
#     all_https = {
#       from_port   = local.https_port
#       to_port     = local.https_port
#       ip_protocol = "tcp"
#       cidr_ipv4   = "0.0.0.0/0"
#     }
#   }
#   security_group_egress_rules = {
#     all = {
#       ip_protocol = "-1"
#       cidr_ipv4   = module.vpc.vpc_cidr_block
#     }
#   }

#   enable_deletion_protection = false

#   listeners = {
#     https = {
#       port     = 443
#       protocol = "TCP"

#       forward = {
#         target_group_key = local.target_group_name
#       }
#     }
#   }

#   target_groups = {
#     (local.target_group_name) = {
#       protocol    = "TCP"
#       port        = local.container_port
#       target_type = "ip"

#       health_check = {
#         enabled           = true
#         healthy_threshold = 5
#         protocol          = "TCP"
#       }

#       create_attachment = false
#     }
#   }
#   tags = local.tags
# }

# resource "aws_route53_record" "proxy" {
#   zone_id = local.route53_zone_id
#   name    = "proxy.aws-is-the-best.com"
#   type    = "A"

#   alias {
#     name                   = module.nlb.dns_name
#     zone_id                = module.nlb.zone_id
#     evaluate_target_health = true
#   }
# }

#trivy:ignore:AWS-0178
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = local.name
  cidr = local.vpc_cidr

  azs            = local.azs
  public_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 48)]

  tags = local.tags
}

# ephemeral "aws_secretsmanager_random_password" "password" {
#   password_length     = 16
#   exclude_punctuation = true
# }

# resource "aws_secretsmanager_secret" "creds" {
#   description = "Credentials for authentication in proxy"
#   name        = "proxy/creds"
# }

# resource "aws_secretsmanager_secret_version" "creds" {
#   secret_id = resource.aws_secretsmanager_secret.creds.arn
#   secret_string_wo = jsonencode({
#     username = "admin"
#     password = ephemeral.aws_secretsmanager_random_password.password.random_password
#   })
#   secret_string_wo_version = 1
# }
