# ElastiCache Redis configuration

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-cache-subnet"
  }
}

# ElastiCache Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  family = "redis7"
  name   = "${var.project_name}-${var.environment}-cache-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  parameter {
    name  = "maxclients"
    value = "10000"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-cache-params"
  }
}

# KMS Key for ElastiCache encryption
resource "aws_kms_key" "elasticache" {
  description             = "ElastiCache encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-elasticache-encryption-key"
  }
}

resource "aws_kms_alias" "elasticache" {
  name          = "alias/${var.project_name}-elasticache-encryption-key"
  target_key_id = aws_kms_key.elasticache.key_id
}

# ElastiCache Replication Group
resource "aws_elasticache_replication_group" "main" {
  replication_group_id         = "${var.project_name}-${var.environment}-redis"
  description                  = "Redis cluster for ${var.project_name}"
  
  # Node configuration
  node_type               = var.elasticache_node_type
  port                    = var.elasticache_port
  parameter_group_name    = aws_elasticache_parameter_group.main.name
  
  # Cluster configuration
  num_cache_clusters      = var.elasticache_num_cache_nodes
  
  # Network configuration
  subnet_group_name       = aws_elasticache_subnet_group.main.name
  security_group_ids      = [aws_security_group.elasticache.id]
  
  # Engine configuration
  engine_version          = var.elasticache_engine_version
  
  # Security
  at_rest_encryption_enabled = var.enable_encryption
  transit_encryption_enabled = var.enable_encryption
  kms_key_id                = var.enable_encryption ? aws_kms_key.elasticache.arn : null
  auth_token                = var.enable_encryption ? random_password.redis_auth_token.result : null
  
  # Backup configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "03:00-05:00"
  
  # Maintenance
  maintenance_window      = "sun:05:00-sun:07:00"
  
  # Automatic failover
  automatic_failover_enabled = var.elasticache_num_cache_nodes > 1
  multi_az_enabled          = var.elasticache_num_cache_nodes > 1
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.elasticache_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }
  
  # Apply changes immediately (for non-production)
  apply_immediately = var.environment != "production"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

# Redis Auth Token
resource "random_password" "redis_auth_token" {
  length  = 32
  special = true
}

# CloudWatch Log Groups for ElastiCache
resource "aws_cloudwatch_log_group" "elasticache_slow" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}/slow-log"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-elasticache-slow-logs"
  }
}

# ElastiCache User (for Redis 6.0+)
resource "aws_elasticache_user" "main" {
  count         = var.enable_encryption ? 1 : 0
  user_id       = "${var.project_name}-user"
  user_name     = "${var.project_name}-user"
  access_string = "on ~* &* +@all"
  engine        = "REDIS"
  passwords     = [random_password.redis_auth_token.result]

  tags = {
    Name = "${var.project_name}-redis-user"
  }
}

# ElastiCache User Group
resource "aws_elasticache_user_group" "main" {
  count           = var.enable_encryption ? 1 : 0
  engine          = "REDIS"
  user_group_id   = "${var.project_name}-user-group"
  user_ids        = ["default", aws_elasticache_user.main[0].user_id]

  tags = {
    Name = "${var.project_name}-redis-user-group"
  }
}

# Secrets Manager for Redis credentials
resource "aws_secretsmanager_secret" "redis_credentials" {
  name        = "${var.project_name}/${var.environment}/redis/credentials"
  description = "Redis credentials for ${var.project_name}"

  tags = {
    Name = "${var.project_name}-redis-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    host     = aws_elasticache_replication_group.main.configuration_endpoint_address != "" ? aws_elasticache_replication_group.main.configuration_endpoint_address : aws_elasticache_replication_group.main.primary_endpoint_address
    port     = aws_elasticache_replication_group.main.port
    password = var.enable_encryption ? random_password.redis_auth_token.result : ""
    ssl      = var.enable_encryption
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# CloudWatch Alarms for ElastiCache
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors redis cpu utilization"
  alarm_actions       = var.enable_monitoring ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = {
    Name = "${var.project_name}-redis-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors redis memory utilization"
  alarm_actions       = var.enable_monitoring ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = {
    Name = "${var.project_name}-redis-memory-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "500"
  alarm_description   = "This metric monitors redis connection count"
  alarm_actions       = var.enable_monitoring ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.id
  }

  tags = {
    Name = "${var.project_name}-redis-connections-alarm"
  }
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  count = var.enable_monitoring ? 1 : 0
  name  = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name = "${var.project_name}-alerts"
  }
}

resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.enable_monitoring && var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}