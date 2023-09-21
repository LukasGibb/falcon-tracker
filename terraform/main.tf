// -- START: Services

resource "google_service_account" "service_account" {
  account_id   = "subscription-service-account"
  display_name = "Subscription Service Account"
}

module "project-services" {
  source     = "terraform-google-modules/project-factory/google//modules/project_services"
  version    = "~> 14.3"
  project_id = var.project_id
  activate_apis = [
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "eventarc.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "videointelligence.googleapis.com",
  ]
}

resource "random_id" "suffix" {
  byte_length = 2
}

resource "google_storage_bucket" "function_bucket" {
  project       = var.project_id
  name          = format("%s-%s-%s", var.project_id, "functions", random_id.suffix.hex)
  location      = "US"
  force_destroy = true

  depends_on = [module.project-services]
}

// -- END: Services


// -- START: Comparer Function

data "archive_file" "comparer_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/comparer-function"
  output_path = "./tmp/comparer-function.zip"

  depends_on = [module.project-services]
}

resource "google_storage_bucket_object" "comparer_object" {
  source       = data.archive_file.comparer_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.comparer_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function" "comparer_function" {
  name                  = "comparer-function"
  runtime               = "python38"
  project               = var.project_id
  description           = "comparer function"
  trigger_http          = true
  available_memory_mb   = 1024
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.comparer_object.name
  entry_point           = "handle"

  environment_variables = {
    GCP_PROJECT      = var.project_id
    BUCKET_NAME      = google_storage_bucket.comparer_bucket.name
    ANNOTATION_TOPIC = google_pubsub_topic.annotation_event_topic.name
    PERCENTAGE_DIFF  = "0.0"
  }

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "comparer_invoker" {
  project        = google_cloudfunctions_function.comparer_function.project
  region         = google_cloudfunctions_function.comparer_function.region
  cloud_function = google_cloudfunctions_function.comparer_function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

resource "google_cloud_scheduler_job" "comparer_schedule" {
  name             = "trigger-comparer-function"
  project          = var.project_id
  description      = "triggers the comparer function to run"
  schedule         = var.schedule
  time_zone        = "Australia/Melbourne"
  attempt_deadline = "320s"

  retry_config {
    retry_count = 3
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.comparer_function.https_trigger_url
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(format("{\"video_url\":\"%s\"}", var.video_url))
  }

  depends_on = [module.project-services]
}

resource "google_storage_bucket" "comparer_bucket" {
  project       = var.project_id
  name          = format("%s-%s-%s", var.project_id, "comparer", random_id.suffix.hex)
  location      = "US"
  force_destroy = true

  depends_on = [module.project-services]
}

// -- END: Comparer Function


// -- START: Annotation Event

resource "google_pubsub_topic" "annotation_event_topic" {
  name = "annotation-event-topic"

  depends_on = [module.project-services]
}

resource "google_pubsub_subscription" "annotation_event_subscription" {
  name                 = "annotation-event-subscription"
  project              = var.project_id
  topic                = google_pubsub_topic.annotation_event_topic.name
  ack_deadline_seconds = 60

  push_config {
    push_endpoint = google_cloudfunctions_function.annotation_function.https_trigger_url
  }

  depends_on = [module.project-services]
}

resource "google_pubsub_topic_iam_binding" "annotate" {
  topic   = google_pubsub_topic.annotation_event_topic.id
  role    = "roles/pubsub.publisher"
  members = ["serviceAccount:${google_service_account.service_account.email}"]
}

// -- END: Annotation Event


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
  description           = "annotation function"
  trigger_http          = true
  available_memory_mb   = 1024
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.annotation_object.name
  entry_point           = "handle"
  timeout               = 60 + var.capture_time + var.capture_time

  environment_variables = {
    GCP_PROJECT  = var.project_id
    BUCKET_NAME  = google_storage_bucket.annotation_bucket.name
    NOTIFY_TOPIC = google_pubsub_topic.notify_event_topic.name
    CAPTURE_TIME = var.capture_time
  }

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "annotation_invoker" {
  project        = google_cloudfunctions_function.annotation_function.project
  region         = google_cloudfunctions_function.annotation_function.region
  cloud_function = google_cloudfunctions_function.annotation_function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

resource "google_storage_bucket" "annotation_bucket" {
  name          = format("%s-%s-%s", var.project_id, "annotation", random_id.suffix.hex)
  location      = "US"
  force_destroy = true

  depends_on = [module.project-services]
}

// -- END: Annotation Function


// -- START: Notify Event

resource "google_pubsub_topic" "notify_event_topic" {
  name = "notify-event-topic"

  depends_on = [module.project-services]
}

resource "google_pubsub_subscription" "notify_event_subscription" {
  name                 = "notify-event-subscription"
  topic                = google_pubsub_topic.notify_event_topic.name
  ack_deadline_seconds = 60

  push_config {
    push_endpoint = google_cloudfunctions_function.notify_function.https_trigger_url
  }

  depends_on = [module.project-services]
}

resource "google_pubsub_topic_iam_binding" "notify" {
  topic   = google_pubsub_topic.notify_event_topic.id
  role    = "roles/pubsub.publisher"
  members = ["serviceAccount:${google_service_account.service_account.email}"]
}

// -- END: Notify Event


// -- START: Notify Function

data "archive_file" "notify_zip" {
  type        = "zip"
  source_dir  = "../cloud-functions/notify-function"
  output_path = "./tmp/notify-function.zip"

  depends_on = [module.project-services]
}

resource "google_storage_bucket_object" "notify_object" {
  source       = data.archive_file.notify_zip.output_path
  content_type = "application/zip"
  name         = "src-${data.archive_file.notify_zip.output_md5}.zip"
  bucket       = google_storage_bucket.function_bucket.name

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function" "notify_function" {
  name                  = "notify-function"
  runtime               = "python38"
  description           = "notify function"
  trigger_http          = true
  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.notify_object.name
  entry_point           = "handle"

  depends_on = [module.project-services]
}

resource "google_cloudfunctions_function_iam_member" "notify_invoker" {
  project        = google_cloudfunctions_function.notify_function.project
  region         = google_cloudfunctions_function.notify_function.region
  cloud_function = google_cloudfunctions_function.notify_function.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

// -- END: Notify Function
