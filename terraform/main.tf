
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }

  backend "gcs" {}
}

variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

output "environment" {
  value = var.environment
}
