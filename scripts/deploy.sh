#!/bin/bash

# N8N Web Scraper Deployment Script
# This script automates the deployment of the entire infrastructure and application

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="n8n-scraper"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-west-2}"
TERRAFORM_DIR="terraform"
HELM_DIR="helm/n8n-scraper"
K8S_DIR="k8s"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    local tools=("terraform" "kubectl" "helm" "aws" "docker")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed. Please install it first."
            exit 1
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

setup_terraform_backend() {
    log_info "Setting up Terraform backend..."
    
    local bucket_name="${PROJECT_NAME}-${ENVIRONMENT}-terraform-state-$(date +%s)"
    local dynamodb_table="${PROJECT_NAME}-${ENVIRONMENT}-terraform-locks"
    
    # Create S3 bucket for Terraform state
    if ! aws s3api head-bucket --bucket "$bucket_name" 2>/dev/null; then
        log_info "Creating S3 bucket for Terraform state: $bucket_name"
        aws s3api create-bucket \
            --bucket "$bucket_name" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$bucket_name" \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$bucket_name" \
            --server-side-encryption-configuration '{
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }'
    fi
    
    # Create DynamoDB table for state locking
    if ! aws dynamodb describe-table --table-name "$dynamodb_table" &>/dev/null; then
        log_info "Creating DynamoDB table for Terraform locks: $dynamodb_table"
        aws dynamodb create-table \
            --table-name "$dynamodb_table" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
        
        # Wait for table to be active
        aws dynamodb wait table-exists --table-name "$dynamodb_table"
    fi
    
    # Update terraform backend configuration
    cat > "$TERRAFORM_DIR/backend.tf" << EOF
terraform {
  backend "s3" {
    bucket         = "$bucket_name"
    key            = "$ENVIRONMENT/terraform.tfstate"
    region         = "$AWS_REGION"
    dynamodb_table = "$dynamodb_table"
    encrypt        = true
  }
}
EOF
    
    log_success "Terraform backend configured!"
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Get AWS account ID
    local aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_registry="${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ecr_registry"
    
    # Create ECR repositories if they don't exist
    local repositories=("${PROJECT_NAME}-api" "${PROJECT_NAME}-worker" "${PROJECT_NAME}-frontend")
    for repo in "${repositories[@]}"; do
        if ! aws ecr describe-repositories --repository-names "$repo" &>/dev/null; then
            log_info "Creating ECR repository: $repo"
            aws ecr create-repository --repository-name "$repo" --region "$AWS_REGION"
        fi
    done
    
    # Build and push API image
    log_info "Building API image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-api:latest" -f docker/Dockerfile.api .
    docker push "${ecr_registry}/${PROJECT_NAME}-api:latest"
    
    # Build and push Worker image
    log_info "Building Worker image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-worker:latest" -f docker/Dockerfile.worker .
    docker push "${ecr_registry}/${PROJECT_NAME}-worker:latest"
    
    # Build and push Frontend image
    log_info "Building Frontend image..."
    docker build -t "${ecr_registry}/${PROJECT_NAME}-frontend:latest" -f docker/Dockerfile.frontend .
    docker push "${ecr_registry}/${PROJECT_NAME}-frontend:latest"
    
    log_success "Docker images built and pushed!"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars if it doesn't exist
    if [[ ! -f "terraform.tfvars" ]]; then
        log_info "Creating terraform.tfvars file..."
        cat > terraform.tfvars << EOF
# Basic Configuration
aws_region      = "$AWS_REGION"
environment     = "$ENVIRONMENT"
project_name    = "$PROJECT_NAME"
owner_email     = "admin@example.com"

# Network Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
database_subnet_cidrs = ["10.0.100.0/24", "10.0.200.0/24"]

# EKS Configuration
eks_cluster_version = "1.28"
eks_node_instance_types = ["t3.medium"]
eks_node_desired_capacity = 2
eks_node_min_capacity = 1
eks_node_max_capacity = 5

# Application Configuration
app_image_tag = "latest"
app_replicas = 2
worker_replicas = 2
frontend_replicas = 2

# Feature Flags
enable_ai_features = true
enable_realtime_features = true
enable_analytics = true
enable_backup_automation = true
enable_monitoring = true
enable_logging = true
enable_encryption = true

# Security
allowed_cidr_blocks = ["0.0.0.0/0"]

# Cost Optimization
enable_spot_instances = false
monthly_budget_limit = "100"
EOF
        log_warning "Please review and update terraform.tfvars with your specific configuration!"
        read -p "Press Enter to continue after reviewing terraform.tfvars..."
    fi
    
    # Plan and apply
    terraform plan -out=tfplan
    
    log_warning "Review the Terraform plan above. Do you want to proceed with deployment?"
    read -p "Type 'yes' to continue: " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_error "Deployment cancelled."
        exit 1
    fi
    
    terraform apply tfplan
    
    cd ..
    log_success "Infrastructure deployed!"
}

configure_kubectl() {
    log_info "Configuring kubectl..."
    
    # Update kubeconfig
    aws eks update-kubeconfig --region "$AWS_REGION" --name "${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Verify connection
    kubectl cluster-info
    
    log_success "kubectl configured!"
}

deploy_application() {
    log_info "Deploying application..."
    
    local deployment_method="${DEPLOYMENT_METHOD:-helm}"
    
    case "$deployment_method" in
        "helm")
            deploy_with_helm
            ;;
        "kubectl")
            deploy_with_kubectl
            ;;
        "argocd")
            deploy_with_argocd
            ;;
        *)
            log_error "Unknown deployment method: $deployment_method"
            exit 1
            ;;
    esac
}

deploy_with_helm() {
    log_info "Deploying with Helm..."
    
    # Add required Helm repositories
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Create namespace
    kubectl create namespace "$PROJECT_NAME" --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy with Helm
    helm upgrade --install "$PROJECT_NAME" "$HELM_DIR" \
        --namespace "$PROJECT_NAME" \
        --set global.environment="$ENVIRONMENT" \
        --set global.region="$AWS_REGION" \
        --wait --timeout=10m
    
    log_success "Application deployed with Helm!"
}

deploy_with_kubectl() {
    log_info "Deploying with kubectl..."
    
    # Apply Kubernetes manifests
    kubectl apply -f "$K8S_DIR/"
    
    # Wait for deployments to be ready
    kubectl wait --for=condition=available --timeout=600s deployment --all -n "$PROJECT_NAME"
    
    log_success "Application deployed with kubectl!"
}

deploy_with_argocd() {
    log_info "Deploying with ArgoCD..."
    
    # ArgoCD should already be deployed via Terraform
    # The application will be automatically synced
    
    log_info "Waiting for ArgoCD to sync the application..."
    sleep 30
    
    # Check ArgoCD application status
    kubectl get applications -n argocd
    
    log_success "Application will be deployed by ArgoCD!"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    kubectl get pods -n "$PROJECT_NAME"
    
    # Check services
    kubectl get services -n "$PROJECT_NAME"
    
    # Check ingress
    kubectl get ingress -n "$PROJECT_NAME"
    
    # Get application URLs
    local api_url=$(kubectl get ingress "${PROJECT_NAME}-ingress" -n "$PROJECT_NAME" -o jsonpath='{.spec.rules[0].host}')
    if [[ -n "$api_url" ]]; then
        log_success "Application URLs:"
        echo "  API: https://$api_url/api"
        echo "  Frontend: https://$api_url"
        echo "  Health Check: https://$api_url/api/health"
    fi
    
    log_success "Deployment verification complete!"
}

show_next_steps() {
    log_info "Next Steps:"
    echo ""
    echo "1. Configure your application settings:"
    echo "   kubectl edit configmap ${PROJECT_NAME}-config -n ${PROJECT_NAME}"
    echo ""
    echo "2. Set up monitoring dashboards:"
    echo "   kubectl port-forward svc/grafana 3000:80 -n monitoring"
    echo "   Open http://localhost:3000 (admin/admin)"
    echo ""
    echo "3. Access ArgoCD (if enabled):"
    echo "   kubectl port-forward svc/argocd-server 8080:80 -n argocd"
    echo "   Open http://localhost:8080"
    echo ""
    echo "4. View application logs:"
    echo "   kubectl logs -f deployment/${PROJECT_NAME}-api -n ${PROJECT_NAME}"
    echo ""
    echo "5. Scale your application:"
    echo "   kubectl scale deployment ${PROJECT_NAME}-api --replicas=3 -n ${PROJECT_NAME}"
    echo ""
}

cleanup() {
    log_warning "Cleaning up deployment..."
    
    read -p "Are you sure you want to destroy all resources? Type 'yes' to confirm: " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "Cleanup cancelled."
        return
    fi
    
    # Delete Helm releases
    helm uninstall "$PROJECT_NAME" -n "$PROJECT_NAME" || true
    
    # Delete Kubernetes resources
    kubectl delete namespace "$PROJECT_NAME" || true
    
    # Destroy Terraform infrastructure
    cd "$TERRAFORM_DIR"
    terraform destroy -auto-approve
    cd ..
    
    log_success "Cleanup complete!"
}

# Main execution
main() {
    local action="${1:-deploy}"
    
    case "$action" in
        "deploy")
            check_prerequisites
            setup_terraform_backend
            build_and_push_images
            deploy_infrastructure
            configure_kubectl
            deploy_application
            verify_deployment
            show_next_steps
            ;;
        "infrastructure")
            check_prerequisites
            setup_terraform_backend
            deploy_infrastructure
            configure_kubectl
            ;;
        "application")
            check_prerequisites
            configure_kubectl
            deploy_application
            verify_deployment
            ;;
        "images")
            check_prerequisites
            build_and_push_images
            ;;
        "verify")
            verify_deployment
            ;;
        "cleanup")
            cleanup
            ;;
        "help")
            echo "Usage: $0 [deploy|infrastructure|application|images|verify|cleanup|help]"
            echo ""
            echo "Commands:"
            echo "  deploy        - Full deployment (default)"
            echo "  infrastructure - Deploy only infrastructure"
            echo "  application   - Deploy only application"
            echo "  images        - Build and push Docker images"
            echo "  verify        - Verify deployment"
            echo "  cleanup       - Destroy all resources"
            echo "  help          - Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  ENVIRONMENT        - Deployment environment (default: dev)"
            echo "  AWS_REGION         - AWS region (default: us-west-2)"
            echo "  DEPLOYMENT_METHOD  - helm|kubectl|argocd (default: helm)"
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Run '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"