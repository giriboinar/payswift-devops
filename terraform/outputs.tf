output "eks_cluster_name" {
  description = "EKS cluster name (design only — not provisioned)"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS endpoint (design only — not provisioned)"
  value       = aws_db_instance.payswift.address
}
