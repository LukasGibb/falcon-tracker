# falcon-tracker

## Description

This project uses the Google Video Intelligence API to monitor a video stream and notify subscribers when something interesting happens.

## Requirements
- python
- terraform

## Managing the infrastructure with terraform
- Edit the `terraform.tfvars` file to set your project ID
- Authenticate with Google: `gcloud auth application-default login`
- Run the following to create the infrastructure:
    - `cd terraform`
    - `terraform init`
    - `terraform plan`
    - `terraform apply`

- When done, run the following to destroy the infrastructure:
    - `cd terraform` Assuming you aren't already in the folder.
    - `terraform destroy`


## Local Testing

### Running the tracklocal script

This script will use the Google Video Intelligence API to return object tracking annotations for a local video. 

- `pip3 install -r requirements.txt`
- `gcloud init` to set up a config for your project
- `gcloud auth application-default login` to authenticate with GCP
- `python3 tracklocal.py`

### Running the trackstream script

This script will:
- record and save a clip the stream to `/tmp/latest_clip.mp4`
- optionally use the Google Video Intelligence API to return object tracking annotations for the recorded clip 
- show a live view of the stream for a defined time
- apply local (openCV) object tracking within a defined region of interest
- optionally draw contours and bounding boxes around the detected objects
- display the static background mask that is being used to reduce noise
- display the region of interest to help understand which area is being observed


- `pip3 install -r requirements.txt`
- `gcloud init` to set up a config for your project
- `gcloud auth application-default login` to authenticate with GCP
- `python3 trackstream.py`
- To stop the video capture, press the ESC on the keyboard.

### Comparer CloudFunction

This Cloud Function takes the latest frame of the video stream and compares it with the frame that was captured on the last run (stored in the Cloud Bucket).

- `cd cloud-functions\comparer-function\`
- `pip3 install -r requirements.txt`
- Copy `.env.example` to `.env` if it doesn't already exist
- Set the environment variables (copy the values from the terraform output)
- Run `functions-framework --target handle --debug` in terminal to run the function
OR
- Open `main.py` and then press `F5` to use the Run and Debug function in VS Code

Use PostMan to send requests to http://localhost:8080
- Set the `Content-Type` header to `application\json`
- Set the `Body` to `raw` and select `JSON`
- Add the following (updating the URL to your chosen live stream)

```
{
    "video_url": "https://www.youtube.com/watch?v=y3b2rKUPMsA"
}
```

### Annotation CloudFunction

This Cloud Function will:
- capture a clip of the video stream
- send the clip to the video intelligence API for annotation
TODO:
- store the annotation in a bucket for future comparison
- compare the annotation with the one captured on the last run
- sends a message to pub/sub (to trigger the notify-function) if there is something worth hearing about

- `cd cloud-functions\annotate-function\`
- `pip3 install -r requirements.txt`
- Copy `.env.example` to `.env` if it doesn't already exist
- Set the environment variables (copy the values from the terraform output)
- Run `functions-framework --target handle --debug` in terminal to run the function
OR
- Open `main.py` and then press `F5` to use the Run and Debug function in VS Code

Use PostMan to send requests to http://localhost:8080
- Set the `Content-Type` header to `application\json`
- Set the `Body` to `raw` and select `JSON`
- Add the following (updating the URL to your chosen live stream)

```
{
    "video_url": "https://www.youtube.com/watch?v=y3b2rKUPMsA"
}
```
