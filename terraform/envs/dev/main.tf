terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  # region = var.region

  default_tags {
    tags = {
      Project = var.project
      #     Owner       = var.owner
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name = "${var.project}-dev"
}

module "network" {
  source = "../../modules/network"

  name          = local.name
  app_port      = var.app_port
  allowed_cidrs = var.allowed_cidrs
}

module "ecr" {
  source = "../../modules/ecr"

  name = local.name
}

module "ecs" {
  source = "../../modules/ecs"

  name                 = local.name
  image_repository_url = module.ecr.repository_url
  image_tag            = var.image_tag
  subnet_ids           = module.network.public_subnet_ids
  security_group_id    = module.network.app_security_group_id
  app_port             = var.app_port
  desired_count        = var.desired_count
}