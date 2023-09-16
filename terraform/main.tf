// -- START: Services

module "project-services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.3"

  project_id = var.project_id

  activate_apis = [
    "compute.googleapis.com",
    "iam.googleapis.com",
    "cloudfunctions.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "videointelligence.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com"
  ]
}

resource "random_id" "suffix" {
  byte_length = 2
}

resource "google_storage_bucket" "function_bucket" {
  project    = var.project_id
  name       = format("%s-%s-%s", var.project_id, "functions", random_id.suffix.hex)
  location   = "US"
  depends_on = [module.project-services]
}

// -- END: Services


// -- START: Comparer Function

data "archive_file" "comparer_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/comparer-function"
  output_path = "./tmp/comparer-function.zip"
  depends_on  = [module.project-services]
}

resource "google_storage_bucket_object" "comparer_object" {
  source       = data.archive_file.comparer_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.comparer_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name
  depends_on   = [module.project-services]
}

resource "google_cloudfunctions_function" "comparer_function" {
  name                  = "comparer-function"
  runtime               = "python38"
  project               = var.project_id
  region                = "us-central1"
  description           = "comparer function"
  trigger_http          = true
  available_memory_mb   = 1024
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.comparer_object.name
  entry_point           = "handle"

  environment_variables = {
    BUCKET_NAME = google_storage_bucket.comparer_bucket.name
    BYPASS      = false
  }

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "comparer_invoker" {
  project        = google_cloudfunctions_function.comparer_function.project
  region         = google_cloudfunctions_function.comparer_function.region
  cloud_function = google_cloudfunctions_function.comparer_function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

resource "google_cloud_scheduler_job" "trigger_comparer_function" {
  name             = "trigger-main-function"
  project          = var.project_id
  description      = "triggers the main function to run"
  schedule         = "*/10 * * * *"
  time_zone        = "Australia/Melbourne"
  attempt_deadline = "320s"
  region           = "us-central1"

  retry_config {
    retry_count = 3
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.comparer_function.https_trigger_url
    body        = base64encode(format("{\"video_url\":\"%s\"}", var.video_url))
  }

  depends_on = [module.project-services]
}

resource "google_storage_bucket" "comparer_bucket" {
  project    = var.project_id
  name       = format("%s-%s-%s", var.project_id, "comparer", random_id.suffix.hex)
  location   = "US"
  depends_on = [module.project-services]
}

// -- END: Comparer Function


// -- START: Annotation Function

data "archive_file" "annotation_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/annotation-function"
  output_path = "./tmp/annotation-function.zip"
  depends_on  = [module.project-services]
}

resource "google_storage_bucket_object" "annotation_object" {
  source       = data.archive_file.annotation_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.annotation_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name
  depends_on   = [module.project-services]
}

resource "google_cloudfunctions_function" "annotation_function" {
  name                  = "annotation-function"
  runtime               = "python38"
  project               = var.project_id
  region                = "us-central1"
  description           = "annotation function"
  trigger_http          = true
  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.annotation_object.name
  entry_point           = "handle"
  depends_on            = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "annotation_invoker" {
  project        = google_cloudfunctions_function.annotation_function.project
  region         = google_cloudfunctions_function.annotation_function.region
  cloud_function = google_cloudfunctions_function.annotation_function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

resource "google_storage_bucket" "annotation_bucket" {
  project    = var.project_id
  name       = format("%s-%s-%s", var.project_id, "annotation", random_id.suffix.hex)
  location   = "US"
  depends_on = [module.project-services]
}

// -- END: Annotation Function


// -- START: Annotation Bucket Event

resource "google_storage_notification" "notification" {
  bucket         = google_storage_bucket.annotation_bucket.name
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.annotation_event_topic.id
  event_types    = ["OBJECT_FINALIZE"]

  depends_on = [google_pubsub_topic_iam_binding.binding]
}

data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

resource "google_pubsub_topic_iam_binding" "binding" {
  project = var.project_id
  topic   = google_pubsub_topic.annotation_event_topic.id
  role    = "roles/pubsub.publisher"
  members = ["serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"]
}

// -- END: Annotation Bucket Event


// -- START: Annotation Event

resource "google_pubsub_topic" "annotation_event_topic" {
  name       = "annotation-event-topic"
  project    = var.project_id
  depends_on = [module.project-services]
}

resource "google_pubsub_subscription" "annotation_event_subscription" {
  name                 = "annotation-event-subscription"
  project              = var.project_id
  topic                = google_pubsub_topic.annotation_event_topic.name
  ack_deadline_seconds = 30
  push_config {
    push_endpoint = google_cloudfunctions_function.analyser_function.https_trigger_url
  }
  depends_on = [module.project-services]
}

// -- END: Annotation Event


// -- START: Analyser Function

data "archive_file" "analyser_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/analyser-function"
  output_path = "./tmp/analyser-function.zip"
  depends_on  = [module.project-services]
}

resource "google_storage_bucket_object" "analyser_object" {
  source       = data.archive_file.analyser_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.analyser_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name
  depends_on   = [module.project-services]
}

resource "google_cloudfunctions_function" "analyser_function" {
  name                  = "analyser-function"
  runtime               = "python38"
  project               = var.project_id
  region                = "us-central1"
  description           = "analyser function"
  trigger_http          = true
  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.analyser_object.name
  entry_point           = "handle"
  depends_on            = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "analyser_invoker" {
  project        = google_cloudfunctions_function.analyser_function.project
  region         = google_cloudfunctions_function.analyser_function.region
  cloud_function = google_cloudfunctions_function.analyser_function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

// -- END: Analyser Function


// -- START: Notification Event

resource "google_pubsub_topic" "notification_event_topic" {
  name       = "notification-event-topic"
  project    = var.project_id
  depends_on = [module.project-services]
}

resource "google_pubsub_subscription" "notification_event_subscription" {
  name                 = "notification-event-subscription"
  project              = var.project_id
  topic                = google_pubsub_topic.notification_event_topic.name
  ack_deadline_seconds = 30
  push_config {
    push_endpoint = google_cloudfunctions_function.notification_function.https_trigger_url
  }
  depends_on = [module.project-services]
}

// -- END: Notification Event


// -- START: Notification Function

data "archive_file" "notification_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/notification-function"
  output_path = "./tmp/notification-function.zip"
  depends_on  = [module.project-services]
}

resource "google_storage_bucket_object" "notification_object" {
  source       = data.archive_file.notification_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.notification_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name
  depends_on   = [module.project-services]
}

resource "google_cloudfunctions_function" "notification_function" {
  name                  = "notification-function"
  runtime               = "python38"
  project               = var.project_id
  region                = "us-central1"
  description           = "notification function"
  trigger_http          = true
  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.notification_object.name
  entry_point           = "handle"
  depends_on            = [module.project-services]
}

// -- END: Analyser Function