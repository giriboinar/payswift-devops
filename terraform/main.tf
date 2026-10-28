# PaySwift Terraform — EKS + RDS Multi-AZ (DESIGN ONLY, NOT APPLIED).
# ---------------------------------------------------------------------------
# This code defines what a real deployment WOULD look like. It has never
# been applied: applying it provisions paid AWS resources (EKS, RDS
# Multi-AZ, NAT) and needs real AWS credentials, which this project
# deliberately does not have. The runnable path is docker compose locally
# (see README.md). Do not run `terraform apply` without a cost review.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Two AZs in the chosen region; EKS nodes and the RDS standby live here.
data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  # Public VPC module, pinned by version in a real setup.
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "payswift-demo"
  cidr = "10.20.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.20.1.0/24", "10.20.2.0/24"]
  public_subnets  = ["10.20.101.0/24", "10.20.102.0/24"]
  database_subnets = ["10.20.201.0/24", "10.20.202.0/24"]

  create_database_subnet_group = true

  enable_nat_gateway = true
  single_nat_gateway = true # cheaper for a demo; production uses one per AZ
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.24.0"

  cluster_name    = "payswift-demo"
  cluster_version = "1.30"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    api = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 2
      desired_size   = 1
    }
  }
}

# RDS Postgres, Multi-AZ: AWS keeps a synchronous standby in the second AZ
# and fails over automatically. The local compose stack simulates this same
# shape with a primary + streaming-replica pair (see scripts/failover_demo.sh).
resource "aws_db_instance" "payswift" {
  identifier           = "payswift-demo"
  engine               = "postgres"
  engine_version       = "16.4"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  multi_az             = true
  db_name              = "payswift"
  username             = var.db_username
  password             = var.db_password # pass via -var or TF_VAR_, never commit
  skip_final_snapshot  = true
  deletion_protection  = false
  publicly_accessible  = false
  vpc_security_group_ids = [module.vpc.default_security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name
}
