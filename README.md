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

### Comparer Function

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

### Running the tracklocal script

This script will use the Google Video Intelligence API to return object tracking annotations for a local video. 

- `pip3 install -r requirements.txt`
- `gcloud init` to set up a config for your project
- `gcloud auth application-default login` to authenticate with GCP
- `python3 tracklocal.py`

### Annotation Function

- `cd cloud-functions\annotate-function\`
- `pip3 install -r requirements.txt`
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
