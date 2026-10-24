terraform {
  backend "s3" {
    bucket       = "finops-guard-tfstate-730335664607"
    key          = "dev/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}