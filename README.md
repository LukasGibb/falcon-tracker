# falcon-tracker

## Description

This project uses the Google Video Intelligence API to monitor a video stream and notify subscribers when something interesting happens.

## Requirements
- Python

## Running the tracklocal script

This script will use the Google Video Intelligence API to return object tracking annotations for a local video. 

- `pip3 install -r requirements.txt`
- `gcloud init`
- `gcloud auth application-default login`
- `python3 tracklocal.py`
