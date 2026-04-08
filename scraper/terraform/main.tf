provider "aws" {
  region = local.region
}

data "terraform_remote_state" "proxy" {
  backend = "s3"
  config = {
    bucket = "aws-is-the-best-terraform-state"
    key    = "job-prospector/proxy/terraform.tfstate"
    region = local.region
  }
}

data "aws_caller_identity" "current" {}

locals {
  region     = "eu-central-1"
  name       = "scraper"
  account_id = data.aws_caller_identity.current.account_id

  ecr_image = "${resource.aws_ecr_repository.scraper.repository_url}:${var.image_tag}"

  vpc_id             = data.terraform_remote_state.proxy.outputs.vpc_id
  public_subnets     = data.terraform_remote_state.proxy.outputs.public_subnets
  vpc_cidr_block     = data.terraform_remote_state.proxy.outputs.vpc_cidr_block
  https_port         = 443
  period             = 60
  evaluation_periods = 5
  github_repository  = "cheburechko/job-prospector"

  tags = {
    name = local.name
  }
}

################################################################################
# ECR
################################################################################

resource "aws_ecr_repository" "scraper" {
  name                 = "job-prospector/scraper"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = false
  }
}

################################################################################
# GitHub Actions OIDC -> ECR push role
################################################################################

# If this OIDC provider already exists in the account from another project,
# replace this resource with: data "aws_iam_openid_connect_provider" "github" { url = "..." }
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  tags = local.tags
}

resource "aws_iam_role" "ecr_push" {
  name = "${local.name}-gha-ecr-push"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${local.github_repository}:*"
          }
        }
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "ecr_push" {
  name = "${local.name}-gha-ecr-push"
  role = aws_iam_role.ecr_push.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:BatchGetImage",
        ]
        Resource = aws_ecr_repository.scraper.arn
      }
    ]
  })
}

################################################################################
# DynamoDB
################################################################################

resource "aws_dynamodb_table" "site_configs" {
  name         = "scraper-site-configs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "company"

  attribute {
    name = "company"
    type = "S"
  }

  tags = local.tags
}

resource "aws_dynamodb_table" "jobs" {
  name         = "scraper-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "company"
  range_key    = "url"

  attribute {
    name = "company"
    type = "S"
  }

  attribute {
    name = "url"
    type = "S"
  }

  tags = local.tags
}

################################################################################
# SQS
################################################################################

resource "aws_sqs_queue" "tasks" {
  name                       = "scraper-tasks"
  visibility_timeout_seconds = 300

  tags = local.tags
}

################################################################################
# ECS Cluster + Worker Service
################################################################################

module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "7.3.1"

  cluster_name = local.name

  cluster_capacity_providers = ["FARGATE_SPOT"]
  default_capacity_provider_strategy = {
    FARGATE_SPOT = {
      weight = 100
    }
  }

  services = {
    worker = {
      assign_public_ip = true
      cpu              = 1024
      memory           = 2048

      # Autoscaling managed externally via appautoscaling
      autoscaling_min_capacity = 0
      autoscaling_max_capacity = 1
      autoscaling_policies     = {}
      desired_count            = 0

      container_definitions = {
        worker = {
          cpu       = 1024
          memory    = 2048
          essential = true
          image     = local.ecr_image

          readonlyRootFilesystem = false

          command = ["worker"]

          environment = [
            { name = "DYNAMODB_CONFIGS_TABLE", value = resource.aws_dynamodb_table.site_configs.name },
            { name = "DYNAMODB_JOBS_TABLE", value = resource.aws_dynamodb_table.jobs.name },
            { name = "DYNAMODB_REGION", value = local.region },
            { name = "SQS_QUEUE_URL", value = aws_sqs_queue.tasks.url },
            { name = "SQS_REGION", value = local.region },
            { name = "SCRAPER_MAX_CONCURRENCY", value = "1000" },
            { name = "SCRAPER_RPS", value = "0.1" },
          ]

          memoryReservation = 256

          restartPolicy = {
            enabled              = true
            restartAttemptPeriod = 60
          }
        }
      }

      deployment_configuration = {
        strategy = "ROLLING"
      }

      tasks_iam_role_statements = [
        {
          effect = "Allow"
          actions = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan",
          ]
          resources = [
            aws_dynamodb_table.site_configs.arn,
            aws_dynamodb_table.jobs.arn,
          ]
        },
        {
          effect = "Allow"
          actions = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
          ]
          resources = [aws_sqs_queue.tasks.arn]
        }
      ]

      subnet_ids                    = local.public_subnets
      vpc_id                        = local.vpc_id
      availability_zone_rebalancing = "ENABLED"

      security_group_ingress_rules = {
        vpc_https = {
          description = "VPC https"
          ip_protocol = "tcp"
          cidr_ipv4   = local.vpc_cidr_block
          from_port   = local.https_port
          to_port     = local.https_port
        }
      }
      security_group_egress_rules = {
        all = {
          cidr_ipv4   = "0.0.0.0/0"
          ip_protocol = "-1"
        }
      }
    },
  }

  tags = local.tags
}

################################################################################
# Scheduler Task Definition
################################################################################

resource "aws_iam_role" "scheduler" {
  name = "${local.name}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${local.name}-scheduler"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:GetItem",
        ]
        Resource = [
          aws_dynamodb_table.site_configs.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
        ]
        Resource = [aws_sqs_queue.tasks.arn]
      }
    ]
  })
}

resource "aws_iam_role" "scheduler_exec" {
  name = "${local.name}-scheduler-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "scheduler_exec" {
  name = "${local.name}-scheduler-exec"
  role = aws_iam_role.scheduler_exec.id

  policy = jsonencode({
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents",
          "logs:CreateLogStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
    ],
    Version = "2012-10-17"
  })
}

resource "aws_security_group" "vpc_https" {
  name   = "${local.name}-vpc-https"
  vpc_id = local.vpc_id

  ingress {
    from_port   = local.https_port
    to_port     = local.https_port
    protocol    = "tcp"
    cidr_blocks = [local.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_ecs_task_definition" "scheduler" {
  family = "${local.name}-scheduler"
  cpu    = 1024
  memory = 2048

  task_role_arn      = aws_iam_role.scheduler.arn
  execution_role_arn = aws_iam_role.scheduler_exec.arn

  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]

  container_definitions = jsonencode([
    {
      name             = "scheduler"
      assign_public_ip = true
      cpu              = 1024
      memory           = 2048
      essential        = true
      image            = local.ecr_image

      readonlyRootFilesystem = false

      command = ["scheduler"]

      environment = [
        { name = "DYNAMODB_CONFIGS_TABLE", value = resource.aws_dynamodb_table.site_configs.name },
        { name = "DYNAMODB_JOBS_TABLE", value = resource.aws_dynamodb_table.jobs.name },
        { name = "DYNAMODB_REGION", value = local.region },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.tasks.url },
        { name = "SQS_REGION", value = local.region },
      ]

      memoryReservation = 256

      restartPolicy = {
        enabled              = true
        restartAttemptPeriod = 60
        ignoredExitCodes     = [0]
      }
    }
  ])

  tags = local.tags
}

################################################################################
# Worker Autoscaling (scale to zero based on SQS queue depth)
################################################################################

resource "aws_cloudwatch_metric_alarm" "queue_has_messages" {
  alarm_name          = "${local.name}-queue-has-messages"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = local.period
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "Scale up worker when messages are in the queue"

  dimensions = {
    QueueName = aws_sqs_queue.tasks.name
  }

  alarm_actions = [aws_appautoscaling_policy.scale_out.arn]

  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "queue_empty" {
  alarm_name          = "${local.name}-queue-empty"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = local.evaluation_periods
  alarm_actions       = [aws_appautoscaling_policy.scale_in.arn]
  threshold           = 0

  metric_query {
    id          = "e1"
    expression  = "m1 + m2"
    return_data = true
    label       = "Total messages"
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "ApproximateNumberOfMessagesNotVisible"
      namespace   = "AWS/SQS"
      period      = local.period
      stat        = "Maximum"
      dimensions = {
        QueueName = aws_sqs_queue.tasks.name
      }
    }
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      period      = local.period
      stat        = "Maximum"
      dimensions = {
        QueueName = aws_sqs_queue.tasks.name
      }
    }
  }

  alarm_description = "No tasks are being processed"

  tags = local.tags
}

resource "aws_appautoscaling_target" "worker" {
  max_capacity       = 1
  min_capacity       = 0
  resource_id        = "service/${module.ecs.cluster_name}/${module.ecs.services.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [module.ecs]

  tags = local.tags
}

resource "aws_appautoscaling_policy" "scale_out" {
  name               = "${local.name}-scale-out"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = local.period
    metric_aggregation_type = "Maximum"

    step_adjustment {
      scaling_adjustment          = 1
      metric_interval_lower_bound = 0
    }
  }
}

resource "aws_appautoscaling_policy" "scale_in" {
  name               = "${local.name}-scale-in"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = local.period * local.evaluation_periods
    metric_aggregation_type = "Maximum"

    step_adjustment {
      scaling_adjustment          = 0
      metric_interval_upper_bound = 0
    }
  }
}

################################################################################
# EventBridge Schedule
################################################################################

resource "aws_iam_role" "scheduler_eventbridge" {
  name = "${local.name}-eventbridge-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "scheduler_eventbridge" {
  name = "${local.name}-eventbridge-scheduler"
  role = aws_iam_role.scheduler_eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = aws_ecs_task_definition.scheduler.arn
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = aws_iam_role.scheduler_exec.arn
      },
      {
        Effect   = "Allow"
        Action   = "ecs:TagResource"
        Resource = "*"
        Condition = {
          StringEquals = { "ecs:CreateAction" = ["RunTask"] }
        }
      }
    ]
  })
}

resource "aws_scheduler_schedule_group" "scraper" {
  name = "scraper"
}

resource "aws_scheduler_schedule" "daily_scrape" {
  name       = "${local.name}-daily"
  group_name = aws_scheduler_schedule_group.scraper.name

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 0 * * ? *)"

  target {
    arn      = module.ecs.cluster_arn
    role_arn = aws_iam_role.scheduler_eventbridge.arn
    ecs_parameters {
      task_count          = 1
      task_definition_arn = aws_ecs_task_definition.scheduler.arn
      network_configuration {
        assign_public_ip = true
        subnets          = local.public_subnets
        security_groups  = [aws_security_group.vpc_https.id]
      }
    }
    retry_policy {
      maximum_event_age_in_seconds = 1800
      maximum_retry_attempts       = 5
    }
  }
}
