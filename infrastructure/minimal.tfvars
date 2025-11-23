# Minimal deployment configuration for 10 users
aws_region = "us-west-2"
environment = "minimal"

# Use free tier eligible instance
instance_type = "t3.micro"

# Minimal storage
root_volume_size = 8  # GB (free tier eligible)

# Tags for cost tracking
tags = {
  Project     = "AutoStack"
  Environment = "Minimal"
  Users       = "10"
  CostCenter  = "Development"
}