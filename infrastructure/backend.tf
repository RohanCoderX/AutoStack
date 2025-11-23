terraform {
  backend "s3" {
    bucket = "autostack-state-503767747826-1763921007"
    key    = "minimal/terraform.tfstate"
    region = "ap-south-1"
  }
}
