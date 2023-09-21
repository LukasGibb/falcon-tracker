variable "project_id" {
  description = "The ID of the project."
  type        = string
}

variable "video_url" {
  description = "The youtube video url."
  type        = string
}

variable "schedule" {
  description = "The cron schedule for the main function trigger."
  type        = string
}

variable "capture_time" {
  description = "The length of time (sec) to capture video for analysis"
  type        = number
}