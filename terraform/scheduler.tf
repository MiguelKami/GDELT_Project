resource "google_cloud_scheduler_job" "gdelt_scheduler" {
  name = "gdelt_scheduler-${var.environment}"
  description = "project scheduler"
  region = "us-central1"

  schedule = local.isdev ? "5 14 1 1 *" : "0 7,19 * * *"

  time_zone   = "America/Vancouver"

  http_target {
    http_method = "POST"
    uri = google_cloudfunctions2_function.gdelt_ingestion.service_config[0].uri

    headers = {"Content-Type" = "application/json" }
    body = base64encode(jsonencode({tentative = 1}))

    oidc_token {
      service_account_email = google_service_account_iam_member.github_build_user.email
      audience = google_cloudfunctions2_function.gdelt_ingestion.service_config[0].uri
    }
  }
}