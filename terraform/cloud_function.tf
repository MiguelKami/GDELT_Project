
data "archive_file" "gdelt_source" {
  type        = "zip"
  source_dir  = "${path.module}/../code/cloud_function"
  output_path = "${path.module}/gdelt_source.zip"
}

# resource "google_storage_bucket_object" "gdelt_source" {
#   name   = "functions/gdelt_${data.archive_file.gdelt_source.output_md5}.zip"
#   bucket = google_storage_bucket.raw.name
#   source = data.archive_file.gdelt_source.output_path
# }

# resource "google_cloudfunctions2_function" "gdelt_ingestion" {
#   name        = "gdelt-ingestion-${var.environment}"
#   location    = "us-central1"
#   description = "GDELT data ingestion function"

#   build_config {
#     runtime     = "python312"
#     entry_point = "ingest_gdelt"

#     source {
#       storage_source {
#         bucket = google_storage_bucket.raw.name
#         object = google_storage_bucket_object.gdelt_source.name
#       }
#     }
#   }

#   service_config {
#     available_memory                 = "512M"
#     timeout_seconds                  = 540
#     min_instance_count               = 0
#     max_instance_count               = 1
#     max_instance_request_concurrency = 1

#     environment_variables = {
#       GDELT_BASE_URL = "https://data.gdeltproject.org/gdeltv2"
#     }
#   }

#   depends_on = [
#     google_project_service.services
#   ]
# }
