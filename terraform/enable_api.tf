locals {
  api = ["secretmanager.googleapis.com"]
}

resource "google_project_service" "services" {
    for_each = toset(local.api)
    
    project = var.project_id
    service = each.value
    disable_on_destroy = false
}