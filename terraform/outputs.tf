# Terraform outputs for n8n-scraper infrastructure

# VPC outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

# EKS outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = aws_eks_cluster.main.id
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = aws_eks_cluster.main.arn
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}

output "eks_node_group_arn" {
  description = "EKS node group ARN"
  value       = aws_eks_node_group.main.arn
}

output "eks_node_group_status" {
  description = "EKS node group status"
  value       = aws_eks_node_group.main.status
}

# RDS outputs
output "rds_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "rds_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

# ElastiCache outputs
output "elasticache_cluster_id" {
  description = "ElastiCache cluster ID"
  value       = aws_elasticache_replication_group.main.replication_group_id
}

output "elasticache_cluster_address" {
  description = "ElastiCache cluster address"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "elasticache_port" {
  description = "ElastiCache port"
  value       = aws_elasticache_replication_group.main.port
}

# S3 outputs
output "s3_bucket_name" {
  description = "S3 bucket name for application data"
  value       = aws_s3_bucket.app_data.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.app_data.arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.app_data.bucket_domain_name
}

# IAM outputs
output "eks_cluster_role_arn" {
  description = "EKS cluster IAM role ARN"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_group_role_arn" {
  description = "EKS node group IAM role ARN"
  value       = aws_iam_role.eks_nodes.arn
}

# Security Group outputs
output "eks_cluster_additional_security_group_id" {
  description = "EKS cluster additional security group ID"
  value       = aws_security_group.eks_cluster.id
}

output "eks_nodes_security_group_id" {
  description = "EKS nodes security group ID"
  value       = aws_security_group.eks_nodes.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "elasticache_security_group_id" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.elasticache.id
}

# CloudWatch outputs
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.app_logs.arn
}

# Load Balancer outputs
output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "Application Load Balancer ARN"
  value       = aws_lb.main.arn
}

# Route53 outputs
output "route53_zone_id" {
  description = "Route53 hosted zone ID"
  value       = var.domain_name != "" ? aws_route53_zone.main[0].zone_id : null
}

output "route53_name_servers" {
  description = "Route53 name servers"
  value       = var.domain_name != "" ? aws_route53_zone.main[0].name_servers : null
}

# ACM outputs
output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = var.enable_ssl && var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
}

# Application URLs
output "application_url" {
  description = "Application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
}

output "api_url" {
  description = "API URL"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : "http://${aws_lb.main.dns_name}/api"
}

# Database connection information
output "database_url" {
  description = "Database connection URL"
  value       = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "redis://:${random_password.redis_auth_token.result}@${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  sensitive   = true
}

# Kubernetes configuration
output "kubeconfig_command" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}

# Helm deployment information
output "helm_release_name" {
  description = "Helm release name"
  value       = helm_release.n8n_scraper.name
}

output "helm_release_namespace" {
  description = "Helm release namespace"
  value       = helm_release.n8n_scraper.namespace
}

output "helm_release_status" {
  description = "Helm release status"
  value       = helm_release.n8n_scraper.status
}

# ArgoCD information
output "argocd_server_url" {
  description = "ArgoCD server URL"
  value       = var.enable_argocd ? "https://argocd.${var.domain_name != "" ? var.domain_name : aws_lb.main.dns_name}" : null
}

output "argocd_admin_password" {
  description = "ArgoCD admin password"
  value       = var.enable_argocd ? random_password.argocd_admin.result : null
  sensitive   = true
}

# Monitoring URLs
output "prometheus_url" {
  description = "Prometheus URL"
  value       = var.enable_monitoring ? "https://prometheus.${var.domain_name != "" ? var.domain_name : aws_lb.main.dns_name}" : null
}

output "grafana_url" {
  description = "Grafana URL"
  value       = var.enable_monitoring ? "https://grafana.${var.domain_name != "" ? var.domain_name : aws_lb.main.dns_name}" : null
}

output "grafana_admin_password" {
  description = "Grafana admin password"
  value       = var.enable_monitoring ? random_password.grafana_admin.result : null
  sensitive   = true
}

# Cost information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost (USD)"
  value = {
    eks_cluster    = "$73.00"  # EKS cluster cost
    eks_nodes      = "$${var.eks_node_desired_capacity * 30 * 0.0464}"  # t3.medium cost
    rds           = "$${var.rds_instance_class == \"db.t3.micro\" ? \"12.41\" : \"24.82\"}"  # RDS cost
    elasticache   = "$${var.elasticache_node_type == \"cache.t3.micro\" ? \"11.52\" : \"23.04\"}"  # ElastiCache cost
    load_balancer = "$16.20"   # ALB cost
    nat_gateway   = "$${length(var.public_subnet_cidrs) * 32.40}"  # NAT Gateway cost
    s3            = "~$5.00"    # S3 storage (estimated)
    cloudwatch    = "~$10.00"   # CloudWatch logs (estimated)
    total_estimate = "~$${73 + (var.eks_node_desired_capacity * 30 * 0.0464) + (var.rds_instance_class == \"db.t3.micro\" ? 12.41 : 24.82) + (var.elasticache_node_type == \"cache.t3.micro\" ? 11.52 : 23.04) + 16.20 + (length(var.public_subnet_cidrs) * 32.40) + 15}"
  }
}

# Resource summary
output "resource_summary" {
  description = "Summary of created resources"
  value = {
    vpc_id                = aws_vpc.main.id
    eks_cluster_name      = aws_eks_cluster.main.name
    rds_instance_id       = aws_db_instance.main.id
    elasticache_cluster   = aws_elasticache_replication_group.main.replication_group_id
    s3_bucket            = aws_s3_bucket.app_data.bucket
    load_balancer_dns    = aws_lb.main.dns_name
    application_url      = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.main.dns_name}"
    environment          = var.environment
    region              = var.aws_region
  }
}