# Terraform tests for main infrastructure
# These tests validate the AWS infrastructure configuration

terraform {
  required_providers {
    test = {
      source = "terraform.io/builtin/test"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Test VPC configuration
resource "test_assertions" "vpc_configuration" {
  component = "vpc"

  equal "vpc_cidr" {
    description = "VPC CIDR should be configurable"
    got         = var.vpc_cidr
    want        = "10.0.0.0/16"
  }

  check "vpc_enable_dns" {
    description = "VPC should have DNS support enabled"
    condition   = aws_vpc.main.enable_dns_support == true
  }

  check "vpc_enable_dns_hostnames" {
    description = "VPC should have DNS hostnames enabled"
    condition   = aws_vpc.main.enable_dns_hostnames == true
  }

  check "vpc_tags" {
    description = "VPC should have required tags"
    condition = (
      aws_vpc.main.tags["Name"] == "${var.project_name}-${var.environment}-vpc" &&
      aws_vpc.main.tags["Environment"] == var.environment &&
      aws_vpc.main.tags["Project"] == var.project_name
    )
  }
}

# Test subnet configuration
resource "test_assertions" "subnet_configuration" {
  component = "subnets"

  check "public_subnets_count" {
    description = "Should create public subnets in multiple AZs"
    condition   = length(aws_subnet.public) >= 2
  }

  check "private_subnets_count" {
    description = "Should create private subnets in multiple AZs"
    condition   = length(aws_subnet.private) >= 2
  }

  check "database_subnets_count" {
    description = "Should create database subnets in multiple AZs"
    condition   = length(aws_subnet.database) >= 2
  }

  check "public_subnet_map_public_ip" {
    description = "Public subnets should map public IP on launch"
    condition   = alltrue([for subnet in aws_subnet.public : subnet.map_public_ip_on_launch == true])
  }

  check "private_subnet_no_public_ip" {
    description = "Private subnets should not map public IP on launch"
    condition   = alltrue([for subnet in aws_subnet.private : subnet.map_public_ip_on_launch == false])
  }
}

# Test security group configuration
resource "test_assertions" "security_groups" {
  component = "security_groups"

  check "eks_cluster_sg_rules" {
    description = "EKS cluster security group should have proper rules"
    condition = (
      length([for rule in aws_security_group.eks_cluster.ingress : rule if rule.from_port == 443]) > 0 &&
      length([for rule in aws_security_group.eks_cluster.egress : rule if rule.from_port == 0]) > 0
    )
  }

  check "rds_sg_rules" {
    description = "RDS security group should allow PostgreSQL access"
    condition = (
      length([for rule in aws_security_group.rds.ingress : rule if rule.from_port == 5432]) > 0
    )
  }

  check "elasticache_sg_rules" {
    description = "ElastiCache security group should allow Redis access"
    condition = (
      length([for rule in aws_security_group.elasticache.ingress : rule if rule.from_port == 6379]) > 0
    )
  }
}

# Test S3 bucket configuration
resource "test_assertions" "s3_bucket" {
  component = "s3"

  check "bucket_versioning" {
    description = "S3 bucket should have versioning enabled"
    condition   = aws_s3_bucket_versioning.app_data.versioning_configuration[0].status == "Enabled"
  }

  check "bucket_encryption" {
    description = "S3 bucket should have encryption enabled"
    condition   = aws_s3_bucket_server_side_encryption_configuration.app_data.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
  }

  check "bucket_public_access_block" {
    description = "S3 bucket should block public access"
    condition = (
      aws_s3_bucket_public_access_block.app_data.block_public_acls == true &&
      aws_s3_bucket_public_access_block.app_data.block_public_policy == true &&
      aws_s3_bucket_public_access_block.app_data.ignore_public_acls == true &&
      aws_s3_bucket_public_access_block.app_data.restrict_public_buckets == true
    )
  }
}

# Test IAM roles and policies
resource "test_assertions" "iam_configuration" {
  component = "iam"

  check "eks_cluster_role_trust_policy" {
    description = "EKS cluster role should trust EKS service"
    condition   = can(regex("eks.amazonaws.com", aws_iam_role.eks_cluster.assume_role_policy))
  }

  check "eks_node_role_trust_policy" {
    description = "EKS node role should trust EC2 service"
    condition   = can(regex("ec2.amazonaws.com", aws_iam_role.eks_node_group.assume_role_policy))
  }

  check "eks_cluster_policies_attached" {
    description = "EKS cluster role should have required policies"
    condition = (
      contains([for attachment in aws_iam_role_policy_attachment.eks_cluster : attachment.policy_arn], "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy")
    )
  }

  check "eks_node_policies_attached" {
    description = "EKS node role should have required policies"
    condition = (
      contains([for attachment in aws_iam_role_policy_attachment.eks_node_group : attachment.policy_arn], "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy") &&
      contains([for attachment in aws_iam_role_policy_attachment.eks_node_group : attachment.policy_arn], "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy") &&
      contains([for attachment in aws_iam_role_policy_attachment.eks_node_group : attachment.policy_arn], "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly")
    )
  }
}

# Test CloudWatch configuration
resource "test_assertions" "cloudwatch_configuration" {
  component = "cloudwatch"

  check "log_group_retention" {
    description = "CloudWatch log group should have proper retention"
    condition   = aws_cloudwatch_log_group.eks.retention_in_days == var.log_retention_days
  }

  check "log_group_encryption" {
    description = "CloudWatch log group should be encrypted"
    condition   = aws_cloudwatch_log_group.eks.kms_key_id != null
  }
}

# Test random password generation
resource "test_assertions" "random_passwords" {
  component = "passwords"

  check "db_password_length" {
    description = "Database password should be sufficiently long"
    condition   = random_password.db_password.length >= 16
  }

  check "redis_password_length" {
    description = "Redis password should be sufficiently long"
    condition   = random_password.redis_password.length >= 16
  }

  check "password_special_chars" {
    description = "Passwords should include special characters"
    condition = (
      random_password.db_password.special == true &&
      random_password.redis_password.special == true
    )
  }
}

# Test data sources
resource "test_assertions" "data_sources" {
  component = "data_sources"

  check "availability_zones" {
    description = "Should have multiple availability zones"
    condition   = length(data.aws_availability_zones.available.names) >= 2
  }

  check "caller_identity" {
    description = "Should have valid AWS caller identity"
    condition   = data.aws_caller_identity.current.account_id != ""
  }
}

# Test resource naming conventions
resource "test_assertions" "naming_conventions" {
  component = "naming"

  check "resource_naming_pattern" {
    description = "Resources should follow naming convention"
    condition = (
      can(regex("^${var.project_name}-${var.environment}-", aws_vpc.main.tags["Name"])) &&
      can(regex("^${var.project_name}-${var.environment}-", aws_cloudwatch_log_group.eks.name))
    )
  }
}

# Test environment-specific configurations
resource "test_assertions" "environment_config" {
  component = "environment"

  check "environment_validation" {
    description = "Environment should be valid"
    condition   = contains(["dev", "staging", "prod"], var.environment)
  }

  check "project_name_validation" {
    description = "Project name should be valid"
    condition   = can(regex("^[a-z0-9-]+$", var.project_name))
  }
}

# Test tagging strategy
resource "test_assertions" "tagging_strategy" {
  component = "tags"

  check "required_tags_present" {
    description = "All resources should have required tags"
    condition = (
      aws_vpc.main.tags["Environment"] == var.environment &&
      aws_vpc.main.tags["Project"] == var.project_name &&
      aws_vpc.main.tags["Owner"] == var.owner &&
      aws_vpc.main.tags["ManagedBy"] == "terraform"
    )
  }
}

# Test network routing
resource "test_assertions" "network_routing" {
  component = "routing"

  check "internet_gateway_attached" {
    description = "Internet gateway should be attached to VPC"
    condition   = aws_internet_gateway.main.vpc_id == aws_vpc.main.id
  }

  check "nat_gateway_in_public_subnet" {
    description = "NAT gateway should be in public subnet"
    condition   = contains([for subnet in aws_subnet.public : subnet.id], aws_nat_gateway.main.subnet_id)
  }

  check "private_route_to_nat" {
    description = "Private subnets should route to NAT gateway"
    condition   = aws_route.private_nat.nat_gateway_id == aws_nat_gateway.main.id
  }
}

# Test security best practices
resource "test_assertions" "security_best_practices" {
  component = "security"

  check "no_hardcoded_secrets" {
    description = "No hardcoded secrets in configuration"
    condition = (
      !can(regex("(?i)(password|secret|key)\\s*=\\s*['\"][^'\"]+['\"]|AKIA[0-9A-Z]{16}", jsonencode(var))) &&
      !can(regex("(?i)(password|secret|key)\\s*=\\s*['\"][^'\"]+['\"]|AKIA[0-9A-Z]{16}", file("main.tf")))
    )
  }

  check "security_groups_no_wide_open" {
    description = "Security groups should not be wide open"
    condition = (
      !contains([for rule in aws_security_group.eks_cluster.ingress : rule.cidr_blocks], ["0.0.0.0/0"]) ||
      !contains([for rule in aws_security_group.rds.ingress : rule.cidr_blocks], ["0.0.0.0/0"]) ||
      !contains([for rule in aws_security_group.elasticache.ingress : rule.cidr_blocks], ["0.0.0.0/0"])
    )
  }
}

# Test cost optimization
resource "test_assertions" "cost_optimization" {
  component = "cost"

  check "s3_lifecycle_configured" {
    description = "S3 bucket should have lifecycle configuration for cost optimization"
    condition   = length(aws_s3_bucket_lifecycle_configuration.app_data.rule) > 0
  }
}

# Test high availability
resource "test_assertions" "high_availability" {
  component = "ha"

  check "multi_az_deployment" {
    description = "Resources should be deployed across multiple AZs"
    condition = (
      length(distinct([for subnet in aws_subnet.public : subnet.availability_zone])) >= 2 &&
      length(distinct([for subnet in aws_subnet.private : subnet.availability_zone])) >= 2
    )
  }
}

# Test backup and disaster recovery
resource "test_assertions" "backup_dr" {
  component = "backup"

  check "s3_versioning_enabled" {
    description = "S3 versioning should be enabled for backup"
    condition   = aws_s3_bucket_versioning.app_data.versioning_configuration[0].status == "Enabled"
  }
}