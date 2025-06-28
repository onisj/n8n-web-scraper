# Monitoring and Observability configuration

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  count          = var.enable_monitoring ? 1 : 0
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EKS", "cluster_failed_request_count", "ClusterName", aws_eks_cluster.main.name],
            ["AWS/EKS", "cluster_request_total", "ClusterName", aws_eks_cluster.main.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EKS Cluster Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.id],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", aws_db_instance.main.id],
            ["AWS/RDS", "FreeableMemory", "DBInstanceIdentifier", aws_db_instance.main.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", aws_elasticache_replication_group.main.id],
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "CacheClusterId", aws_elasticache_replication_group.main.id],
            ["AWS/ElastiCache", "CurrConnections", "CacheClusterId", aws_elasticache_replication_group.main.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache Metrics"
          period  = 300
        }
      }
    ]
  })
}

# Application Load Balancer for monitoring services
resource "aws_lb" "monitoring" {
  count              = var.enable_monitoring ? 1 : 0
  name               = "${var.project_name}-${var.environment}-monitoring-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_monitoring[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production"

  tags = {
    Name = "${var.project_name}-monitoring-alb"
  }
}

# Security Group for Monitoring ALB
resource "aws_security_group" "alb_monitoring" {
  count       = var.enable_monitoring ? 1 : 0
  name        = "${var.project_name}-${var.environment}-monitoring-alb-sg"
  description = "Security group for monitoring ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-monitoring-alb-sg"
  }
}

# Target Groups for monitoring services
resource "aws_lb_target_group" "prometheus" {
  count    = var.enable_monitoring ? 1 : 0
  name     = "${var.project_name}-prometheus-tg"
  port     = 9090
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/-/healthy"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-prometheus-tg"
  }
}

resource "aws_lb_target_group" "grafana" {
  count    = var.enable_monitoring ? 1 : 0
  name     = "${var.project_name}-grafana-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-grafana-tg"
  }
}

# ALB Listeners
resource "aws_lb_listener" "monitoring_http" {
  count             = var.enable_monitoring ? 1 : 0
  load_balancer_arn = aws_lb.monitoring[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "monitoring_https" {
  count             = var.enable_monitoring && var.enable_ssl ? 1 : 0
  load_balancer_arn = aws_lb.monitoring[0].arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana[0].arn
  }
}

# Listener Rules
resource "aws_lb_listener_rule" "prometheus" {
  count        = var.enable_monitoring && var.enable_ssl ? 1 : 0
  listener_arn = aws_lb_listener.monitoring_https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus[0].arn
  }

  condition {
    path_pattern {
      values = ["/prometheus*"]
    }
  }
}

# Route53 Records for monitoring
resource "aws_route53_record" "monitoring" {
  count   = var.enable_monitoring && var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "monitoring.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.monitoring[0].dns_name
    zone_id                = aws_lb.monitoring[0].zone_id
    evaluate_target_health = true
  }
}

data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# CloudWatch Log Groups for application logs
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/eks/${var.project_name}-${var.environment}/application"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-application-logs"
  }
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/eks/${var.project_name}-${var.environment}/worker"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-worker-logs"
  }
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/aws/eks/${var.project_name}-${var.environment}/frontend"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-frontend-logs"
  }
}

# CloudWatch Alarms for EKS
resource "aws_cloudwatch_metric_alarm" "eks_node_cpu" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-eks-node-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EKS node CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ClusterName = aws_eks_cluster.main.name
  }

  tags = {
    Name = "${var.project_name}-eks-node-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "eks_node_memory" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-eks-node-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "node_memory_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors EKS node memory utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ClusterName = aws_eks_cluster.main.name
  }

  tags = {
    Name = "${var.project_name}-eks-node-memory-alarm"
  }
}

# Container Insights for EKS
resource "aws_eks_addon" "container_insights" {
  count        = var.enable_monitoring ? 1 : 0
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "amazon-cloudwatch-observability"

  depends_on = [aws_eks_node_group.main]

  tags = {
    Name = "${var.project_name}-container-insights-addon"
  }
}

# X-Ray for distributed tracing
resource "aws_eks_addon" "xray" {
  count        = var.enable_monitoring ? 1 : 0
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "adot"

  depends_on = [aws_eks_node_group.main]

  tags = {
    Name = "${var.project_name}-xray-addon"
  }
}

# IAM Role for CloudWatch Agent
resource "aws_iam_role" "cloudwatch_agent" {
  count = var.enable_monitoring ? 1 : 0
  name  = "${var.project_name}-cloudwatch-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks.arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:amazon-cloudwatch:cloudwatch-agent"
            "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-cloudwatch-agent-role"
  }
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  count      = var.enable_monitoring ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = aws_iam_role.cloudwatch_agent[0].name
}

# Cost monitoring
resource "aws_budgets_budget" "monthly" {
  count       = var.enable_monitoring ? 1 : 0
  name        = "${var.project_name}-${var.environment}-monthly-budget"
  budget_type = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  cost_filter {
    name = "TagKey"
    values = ["Project"]
  }
  
  cost_filter {
    name = "TagValue"
    values = [var.project_name]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type           = "PERCENTAGE"
    notification_type        = "ACTUAL"
    subscriber_email_addresses = var.alert_email != "" ? [var.alert_email] : []
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type           = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_email != "" ? [var.alert_email] : []
  }

  tags = {
    Name = "${var.project_name}-monthly-budget"
  }
}