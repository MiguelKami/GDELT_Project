resource "google_workflows_workflow" "gdelt_pipeline" {
  name        = "gdelt-pipeline-${var.environment}"
  region      = "us-central1"
  description = "Orchestrates GDELT ingestion"

  service_account    = google_service_account.gdelt_build.id
  deletion_protection = false

  user_env_vars = {
    FUNCTION_URL = google_cloudfunctions2_function.gdelt_ingestion.service_config[0].uri
  }

  source_contents = templatefile(
    "${path.module}/workflows/gdelt_ingestion.yaml",
    {
      cf = google_cloudfunctions2_function.gdelt_ingestion.service_config[0].uri
    }
  )

  depends_on = [
    google_project_service.services,
    google_cloud_run_service_iam_member.workflow_invoker,
  ]
}
