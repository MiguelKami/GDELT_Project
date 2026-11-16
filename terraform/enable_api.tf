locals {
  api = ["secretmanager.googleapis.com",
         "cloudfunctions.googleapis.com",
         "cloudbuild.googleapis.com",
         "artifactregistry.googleapis.com",
         "run.googleapis.com",
         "workflows.googleapis.com",
         "workflowexecutions.googleapis.com"
         ]
    }

resource "google_project_service" "services" {
    for_each = toset(local.api)
    
    project = var.project_id
    service = each.value
    disable_on_destroy = false
    }

# locals {
#   api = [
#     "secretmanager.googleapis.com",
#     "cloudfunctions.googleapis.com",
#     "cloudbuild.googleapis.com",
#     "artifactregistry.googleapis.com",
#     "run.googleapis.com"
#   ]
# }