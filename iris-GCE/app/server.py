from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import uvicorn, aiohttp, asyncio
from io import BytesIO
import requests, hashlib

from fastai import *
from fastai.vision import *

from google.cloud import storage

model_name = 'single-class'
model_name = 'multi-class'
model_file_id_multi = '16HFcpNFgn465xyrapyIuDSR0YrciJ6pd'
model_file_id_single = '19xqtsyusFddcSkdCm1hlhW3y6ljGck5L'
model_file_id = model_file_id_multi

classes_multi = ['1', '10', '100', '20', '200', '5', '50', '500', 'euro', 'usd']
classes_single = ['euro/10',
 'euro/100',
 'euro/20',
 'euro/200',
 'euro/5',
 'euro/50',
 'euro/500',
 'usd/1',
 'usd/10',
 'usd/100',
 'usd/20',
 'usd/5',
 'usd/50']
classes = classes_multi
path = Path(__file__).parent

bucket_name = "iris-user-uploads"

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])



def download_file_from_google_drive(id, destination):
    if destination.exists():
        return
    print("Downloading model from Google Drive",end="")
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)
    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)
    save_response_content(response, destination)
    print("done.")

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk: # filter out keep-alive new chunks
                print(".",end="")
                f.write(chunk)

async def setup_learner():
    model_file_name = Path('models')/f'{model_name}.pkl'
    download_file_from_google_drive(model_file_id, path/model_file_name)
    try:
        learn = load_learner(path, model_file_name)
        return learn
    except RuntimeError as e:
        if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
            print(e)
            message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
            raise RuntimeError(message)
        else:
            raise


def upload_blob(bucket_name, img_blob,filename):
    """Uploads a file to the GCS bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)

    print('Uploading user image.')
    destination_blob_name = filename+"-"+hashlib.md5(img_blob).hexdigest()+".png"
    print(destination_blob_name)
    blob = bucket.blob(destination_blob_name)

    print(blob.exists(storage_client))
    if not blob.exists(storage_client):
        blob.upload_from_string(img_blob,content_type='image/png')
        print('File uploaded.'.format(
            destination_blob_name))
    else:
        print('File already uploaded')

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()

@app.route('/')
def index(request):
    html = path/'view'/'index.html'
    return HTMLResponse(html.open().read())

@app.route('/status')
def status(request):
    status = {"online":True}
    return JSONResponse(status)


from threading import Thread

@app.route('/analyze', methods=['POST'])
async def analyze(request):
    data = await request.form()
    img_bytes = await (data['file'].read())
    img = open_image(BytesIO(img_bytes))
    prediction= learn.predict(img)
    response = {'result': str(prediction[0]),
                'classes': str(classes),
                'activations': str(prediction[2])}
    if ("skip_upload" in data) and (data['skip_upload']=="true"):
        response['skip_upload']=True
    else:
        filename="pred-"+str(prediction[0]).replace(";", "_")
        Thread(target=upload_blob, args=(bucket_name, img_bytes,filename)).start()
    print(response)
    return JSONResponse(response)

if __name__ == '__main__':
    if 'serve' in sys.argv: uvicorn.run(app, host='0.0.0.0', port=8080)
