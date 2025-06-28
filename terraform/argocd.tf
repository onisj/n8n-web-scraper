# ArgoCD GitOps configuration

# Kubernetes provider for ArgoCD
provider "kubernetes" {
  alias                  = "argocd"
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.main.token
}

provider "helm" {
  alias = "argocd"
  kubernetes {
    host                   = aws_eks_cluster.main.endpoint
    cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.main.token
  }
}

# ArgoCD Namespace
resource "kubernetes_namespace" "argocd" {
  count = var.enable_argocd ? 1 : 0
  provider = kubernetes.argocd
  
  metadata {
    name = var.argocd_namespace
    
    labels = {
      "app.kubernetes.io/name"     = "argocd"
      "app.kubernetes.io/instance" = "argocd"
    }
  }
  
  depends_on = [aws_eks_node_group.main]
}

# ArgoCD Helm Release
resource "helm_release" "argocd" {
  count      = var.enable_argocd ? 1 : 0
  provider   = helm.argocd
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "5.51.6"
  namespace  = kubernetes_namespace.argocd[0].metadata[0].name
  
  values = [
    yamlencode({
      global = {
        domain = var.domain_name != "" ? "argocd.${var.domain_name}" : "argocd.local"
      }
      
      configs = {
        params = {
          "server.insecure" = var.environment != "production"
        }
        
        cm = {
          "url" = var.domain_name != "" ? "https://argocd.${var.domain_name}" : "http://argocd.local"
          "oidc.config" = yamlencode({
            name = "OIDC"
            issuer = "https://accounts.google.com"
            clientId = var.argocd_oidc_client_id
            clientSecret = var.argocd_oidc_client_secret
            requestedScopes = ["openid", "profile", "email"]
            requestedIDTokenClaims = {
              groups = {
                essential = true
              }
            }
          })
          
          "policy.default" = "role:readonly"
          "policy.csv" = <<-EOT
            p, role:admin, applications, *, */*, allow
            p, role:admin, clusters, *, *, allow
            p, role:admin, repositories, *, *, allow
            p, role:readonly, applications, get, */*, allow
            p, role:readonly, applications, sync, */*, allow
            g, argocd-admins, role:admin
          EOT
        }
        
        rbac = {
          "policy.default" = "role:readonly"
        }
      }
      
      server = {
        replicas = var.environment == "production" ? 2 : 1
        
        autoscaling = {
          enabled = var.environment == "production"
          minReplicas = 2
          maxReplicas = 5
          targetCPUUtilizationPercentage = 70
          targetMemoryUtilizationPercentage = 80
        }
        
        resources = {
          limits = {
            cpu = "500m"
            memory = "512Mi"
          }
          requests = {
            cpu = "250m"
            memory = "256Mi"
          }
        }
        
        service = {
          type = "ClusterIP"
          port = 80
          portName = "http"
        }
        
        ingress = {
          enabled = var.domain_name != ""
          ingressClassName = "nginx"
          hostname = var.domain_name != "" ? "argocd.${var.domain_name}" : null
          tls = var.enable_ssl
          annotations = {
            "nginx.ingress.kubernetes.io/ssl-redirect" = "true"
            "nginx.ingress.kubernetes.io/backend-protocol" = "GRPC"
            "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
          }
        }
      }
      
      controller = {
        replicas = var.environment == "production" ? 2 : 1
        
        resources = {
          limits = {
            cpu = "1000m"
            memory = "1Gi"
          }
          requests = {
            cpu = "500m"
            memory = "512Mi"
          }
        }
        
        metrics = {
          enabled = var.enable_monitoring
          serviceMonitor = {
            enabled = var.enable_monitoring
          }
        }
      }
      
      repoServer = {
        replicas = var.environment == "production" ? 2 : 1
        
        autoscaling = {
          enabled = var.environment == "production"
          minReplicas = 2
          maxReplicas = 5
          targetCPUUtilizationPercentage = 70
          targetMemoryUtilizationPercentage = 80
        }
        
        resources = {
          limits = {
            cpu = "500m"
            memory = "512Mi"
          }
          requests = {
            cpu = "250m"
            memory = "256Mi"
          }
        }
        
        metrics = {
          enabled = var.enable_monitoring
          serviceMonitor = {
            enabled = var.enable_monitoring
          }
        }
      }
      
      applicationSet = {
        enabled = true
        replicas = 1
        
        resources = {
          limits = {
            cpu = "100m"
            memory = "128Mi"
          }
          requests = {
            cpu = "50m"
            memory = "64Mi"
          }
        }
      }
      
      notifications = {
        enabled = var.enable_monitoring
        
        argocdUrl = var.domain_name != "" ? "https://argocd.${var.domain_name}" : "http://argocd.local"
        
        subscriptions = [
          {
            recipients = [var.alert_email]
            triggers = ["on-sync-failed", "on-sync-succeeded"]
          }
        ]
        
        services = {
          slack = {
            token = var.slack_webhook_url
          }
        }
        
        templates = {
          "template.app-sync-succeeded" = {
            message = "Application {{.app.metadata.name}} sync succeeded"
            slack = {
              attachments = [
                {
                  title = "{{.app.metadata.name}}"
                  title_link = "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
                  color = "good"
                  fields = [
                    {
                      title = "Sync Status"
                      value = "{{.app.status.sync.status}}"
                      short = true
                    },
                    {
                      title = "Repository"
                      value = "{{.app.spec.source.repoURL}}"
                      short = true
                    }
                  ]
                }
              ]
            }
          }
          
          "template.app-sync-failed" = {
            message = "Application {{.app.metadata.name}} sync failed"
            slack = {
              attachments = [
                {
                  title = "{{.app.metadata.name}}"
                  title_link = "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
                  color = "danger"
                  fields = [
                    {
                      title = "Sync Status"
                      value = "{{.app.status.sync.status}}"
                      short = true
                    },
                    {
                      title = "Repository"
                      value = "{{.app.spec.source.repoURL}}"
                      short = true
                    }
                  ]
                }
              ]
            }
          }
        }
        
        triggers = {
          "trigger.on-sync-succeeded" = {
            when = "app.status.sync.status == 'Synced'"
            send = ["app-sync-succeeded"]
          }
          
          "trigger.on-sync-failed" = {
            when = "app.status.sync.status == 'Unknown'"
            send = ["app-sync-failed"]
          }
        }
      }
      
      redis = {
        enabled = true
        
        resources = {
          limits = {
            cpu = "200m"
            memory = "256Mi"
          }
          requests = {
            cpu = "100m"
            memory = "128Mi"
          }
        }
      }
    })
  ]
  
  depends_on = [
    kubernetes_namespace.argocd,
    aws_eks_node_group.main
  ]
}

# ArgoCD Application for n8n-scraper
resource "kubernetes_manifest" "argocd_application" {
  count = var.enable_argocd ? 1 : 0
  provider = kubernetes.argocd
  
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    
    metadata = {
      name      = "${var.project_name}-${var.environment}"
      namespace = var.argocd_namespace
      
      labels = {
        "app.kubernetes.io/name"     = var.project_name
        "app.kubernetes.io/instance" = var.environment
      }
      
      finalizers = ["resources-finalizer.argocd.argoproj.io"]
    }
    
    spec = {
      project = "default"
      
      source = {
        repoURL        = var.argocd_git_repo_url
        targetRevision = var.argocd_git_branch
        path           = "helm/n8n-scraper"
        
        helm = {
          valueFiles = ["values-${var.environment}.yaml"]
          
          parameters = [
            {
              name  = "global.environment"
              value = var.environment
            },
            {
              name  = "global.region"
              value = var.aws_region
            },
            {
              name  = "api.image.tag"
              value = var.app_image_tag
            },
            {
              name  = "worker.image.tag"
              value = var.app_image_tag
            },
            {
              name  = "frontend.image.tag"
              value = var.app_image_tag
            }
          ]
        }
      }
      
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = var.project_name
      }
      
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        
        syncOptions = [
          "CreateNamespace=true",
          "PrunePropagationPolicy=foreground",
          "PruneLast=true"
        ]
        
        retry = {
          limit = 5
          backoff = {
            duration    = "5s"
            factor      = 2
            maxDuration = "3m"
          }
        }
      }
      
      revisionHistoryLimit = 10
    }
  }
  
  depends_on = [
    helm_release.argocd,
    kubernetes_namespace.argocd
  ]
}

# ArgoCD Project for better organization
resource "kubernetes_manifest" "argocd_project" {
  count = var.enable_argocd ? 1 : 0
  provider = kubernetes.argocd
  
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "AppProject"
    
    metadata = {
      name      = var.project_name
      namespace = var.argocd_namespace
    }
    
    spec = {
      description = "Project for ${var.project_name} applications"
      
      sourceRepos = [
        var.argocd_git_repo_url,
        "https://charts.bitnami.com/bitnami",
        "https://prometheus-community.github.io/helm-charts",
        "https://grafana.github.io/helm-charts"
      ]
      
      destinations = [
        {
          namespace = var.project_name
          server    = "https://kubernetes.default.svc"
        },
        {
          namespace = "monitoring"
          server    = "https://kubernetes.default.svc"
        }
      ]
      
      clusterResourceWhitelist = [
        {
          group = ""
          kind  = "Namespace"
        },
        {
          group = "rbac.authorization.k8s.io"
          kind  = "ClusterRole"
        },
        {
          group = "rbac.authorization.k8s.io"
          kind  = "ClusterRoleBinding"
        }
      ]
      
      namespaceResourceWhitelist = [
        {
          group = "*"
          kind  = "*"
        }
      ]
      
      roles = [
        {
          name = "admin"
          description = "Admin access to ${var.project_name}"
          policies = [
            "p, proj:${var.project_name}:admin, applications, *, ${var.project_name}/*, allow",
            "p, proj:${var.project_name}:admin, repositories, *, *, allow"
          ]
          groups = ["argocd-admins"]
        },
        {
          name = "developer"
          description = "Developer access to ${var.project_name}"
          policies = [
            "p, proj:${var.project_name}:developer, applications, get, ${var.project_name}/*, allow",
            "p, proj:${var.project_name}:developer, applications, sync, ${var.project_name}/*, allow"
          ]
          groups = ["argocd-developers"]
        }
      ]
    }
  }
  
  depends_on = [
    helm_release.argocd,
    kubernetes_namespace.argocd
  ]
}

# Route53 record for ArgoCD
resource "aws_route53_record" "argocd" {
  count   = var.enable_argocd && var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "argocd.${var.domain_name}"
  type    = "A"
  
  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}