
resource "google_bigquery_dataset" "prep" {
  dataset_id  = "gdelt_prep_${var.environment}"
  description = "GDELT data preparation layer"
  location    = "US"

  labels = {
    environment = var.environment
    layer       = "prep"
  }

}

resource "google_bigquery_table" "event" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "event"
  schema = file("${path.module}/schema/event.json")
  
  external_data_configuration {
    autodetect = true
    source_format = "PARQUET"
    source_uris = ["gs://${google_storage_bucket.raw.name}/data/events/dt=*/"]
    
    hive_partitioning_options {
      mode = "CUSTOM"
      source_uri_prefix = "gs://${google_storage_bucket.raw.name}/data/event/{dt:STRING}"
      require_partition_filter = false
    }
   
   }

}

resource "google_bigquery_table" "mention" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "mention"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
  }

  schema = file("${path.module}/schema/mention.json")

  depends_on = [
    google_bigquery_dataset.prep
  ]
}

resource "google_bigquery_table" "gkg" {
  dataset_id = google_bigquery_dataset.prep.dataset_id
  table_id   = "gkg"

  deletion_protection = local.isprod

  time_partitioning {
    type  = "DAY"
  }

  schema = file("${path.module}/schema/gkg.json")
  
  depends_on = [
    google_bigquery_dataset.prep
  ]
}
