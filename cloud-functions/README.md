# Cloud Functions

## Local testing

Change directory to the target function you want to launch locally

```
cd ./cloud-function/comparer-function
```

Install dependencies

```bash
pip install -r requirements.txt
```

Use the GCP Cloud Framework library to launch target functions `handle` function. This is just the given to the entry function for the HTTP request.

```bash
functions-framework --target=handle
```

The function will silenty launch if there are no issues on `localhost:8080`.

You can now send a curl command to the function:

```bash
curl localhost:8080 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
        "video_url": "https://www.youtube.com/watch?v=y3b2rKUPMsA"
      }'
```

## Further Reading

- https://cloud.google.com/functions/docs/running/function-frameworks 
- https://cloud.google.com/functions/docs/running/calling