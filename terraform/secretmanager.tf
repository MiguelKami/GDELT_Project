resource "google_secret_manager_secret" "api_gdelt" {

    secret_id = "api_gdelt_${var.environment}"

    replication {
        auto {}
    }

    depends_on = [
        google_project_service.services
    ]
}