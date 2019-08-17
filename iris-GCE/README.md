# iris
Detect denomination of money bills, eur and usd for now


This server uses a pre-trained Deep Learning net to detect the denomination of banknotes.

The python server with two pages:

* Main page: It serves a basic HTML that uses JS to select, downsample and POST an image to the server for inference.
* POST service: It receives an image, and runs an inference on the Deep Learning code to identify the banknote bill. It also sotres a copy of the image on Google Storage.

## How to run it

- If ran locally, use a python 3 env, `pip install -r requirements.txt` and then: `python app/server.py serve`.
  If you need to also upload the files to GCE, authenticate the local server with `export GOOGLE_APPLICATION_CREDENTIALS=".iris-auth.json"`
- Ir ran using Docker, use: `docker build .` and then `docker run <build-id>`
- To deploy, use `gcloud app deploy --project GCE-project-id`

<img width="750" alt="Main page" src="https://user-images.githubusercontent.com/434029/62422810-a03b7680-b6b8-11e9-9825-f72a6d622154.png">
