# RDS PostgreSQL Database configuration

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  family = "postgres${split(".", var.rds_engine_version)[0]}"
  name   = "${var.project_name}-${var.environment}-db-params"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_duration"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-db-params"
  }
}

# DB Option Group
resource "aws_db_option_group" "main" {
  name                     = "${var.project_name}-${var.environment}-db-options"
  option_group_description = "Option group for ${var.project_name} PostgreSQL"
  engine_name              = "postgres"
  major_engine_version     = split(".", var.rds_engine_version)[0]

  tags = {
    Name = "${var.project_name}-${var.environment}-db-options"
  }
}

# KMS Key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "RDS encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-rds-encryption-key"
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project_name}-rds-encryption-key"
  target_key_id = aws_kms_key.rds.key_id
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-db"

  # Engine configuration
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  # Storage configuration
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_allocated_storage * 2
  storage_type          = "gp3"
  storage_encrypted     = var.enable_encryption
  kms_key_id           = var.enable_encryption ? aws_kms_key.rds.arn : null

  # Database configuration
  db_name  = replace(var.project_name, "-", "_")
  username = "postgres"
  password = random_password.db_password.result
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.main.name
  option_group_name    = aws_db_option_group.main.name

  # Backup configuration
  backup_retention_period = var.rds_backup_retention_period
  backup_window          = var.rds_backup_window
  maintenance_window     = var.rds_maintenance_window
  copy_tags_to_snapshot  = true
  delete_automated_backups = false

  # High availability
  multi_az = var.rds_multi_az

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Performance Insights
  performance_insights_enabled          = true
  performance_insights_kms_key_id      = var.enable_encryption ? aws_kms_key.rds.arn : null
  performance_insights_retention_period = 7

  # Security
  deletion_protection = var.rds_deletion_protection
  skip_final_snapshot = !var.rds_deletion_protection
  final_snapshot_identifier = var.rds_deletion_protection ? "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Apply changes immediately (for non-production)
  apply_immediately = var.environment != "production"

  tags = {
    Name = "${var.project_name}-${var.environment}-database"
  }

  lifecycle {
    ignore_changes = [password]
  }
}

# Read Replica (for production)
resource "aws_db_instance" "read_replica" {
  count = var.environment == "production" ? 1 : 0

  identifier = "${var.project_name}-${var.environment}-db-read-replica"

  # Replica configuration
  replicate_source_db = aws_db_instance.main.identifier
  instance_class      = var.rds_instance_class

  # Network configuration
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Performance Insights
  performance_insights_enabled          = true
  performance_insights_kms_key_id      = var.enable_encryption ? aws_kms_key.rds.arn : null
  performance_insights_retention_period = 7

  # Security
  deletion_protection = var.rds_deletion_protection
  skip_final_snapshot = !var.rds_deletion_protection

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  tags = {
    Name = "${var.project_name}-${var.environment}-database-read-replica"
    Type = "read-replica"
  }
}

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Group for RDS
resource "aws_cloudwatch_log_group" "rds" {
  name              = "/aws/rds/instance/${aws_db_instance.main.identifier}/postgresql"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-rds-logs"
  }
}

# RDS Proxy (for connection pooling)
resource "aws_db_proxy" "main" {
  count = var.environment == "production" ? 1 : 0

  name                   = "${var.project_name}-${var.environment}-db-proxy"
  engine_family         = "POSTGRESQL"
  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_credentials.arn
  }
  role_arn               = aws_iam_role.db_proxy[0].arn
  vpc_subnet_ids         = aws_subnet.database[*].id
  vpc_security_group_ids = [aws_security_group.rds_proxy[0].id]

  require_tls = true

  tags = {
    Name = "${var.project_name}-${var.environment}-db-proxy"
  }
}

# RDS Proxy Default Target Group
resource "aws_db_proxy_default_target_group" "main" {
  count          = var.environment == "production" ? 1 : 0
  db_proxy_name  = aws_db_proxy.main[0].name

  connection_pool_config {
    max_connections_percent      = 100
    max_idle_connections_percent = 50
    connection_borrow_timeout    = 120
  }
}

# RDS Proxy Target
resource "aws_db_proxy_target" "main" {
  count                  = var.environment == "production" ? 1 : 0
  db_instance_identifier = aws_db_instance.main.identifier
  db_proxy_name          = aws_db_proxy.main[0].name
  target_group_name      = aws_db_proxy_default_target_group.main[0].name
}

# IAM Role for RDS Proxy
resource "aws_iam_role" "db_proxy" {
  count = var.environment == "production" ? 1 : 0
  name  = "${var.project_name}-db-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-db-proxy-role"
  }
}

resource "aws_iam_role_policy" "db_proxy" {
  count = var.environment == "production" ? 1 : 0
  name  = "${var.project_name}-db-proxy-policy"
  role  = aws_iam_role.db_proxy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

# Security Group for RDS Proxy
resource "aws_security_group" "rds_proxy" {
  count       = var.environment == "production" ? 1 : 0
  name        = "${var.project_name}-${var.environment}-rds-proxy-sg"
  description = "Security group for RDS Proxy"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-proxy-sg"
  }
}

# Secrets Manager for database credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/${var.environment}/database/credentials"
  description = "Database credentials for ${var.project_name}"

  tags = {
    Name = "${var.project_name}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = aws_db_instance.main.username
    password = random_password.db_password.result
    engine   = "postgres"
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}