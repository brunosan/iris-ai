# this import statement is needed if you want to use the AWS Lambda Layer called "pytorch-v1-py36"
# it unzips all of the pytorch & dependency packages when the script is loaded to avoid the 250 MB unpacked limit in AWS Lambda
try:
    import unzip_requirements
except ImportError:
    pass

import os
import re
import base64
import io
import json
import tarfile
import glob
import time
import logging

import boto3
import requests
import PIL

import torch
import torch.nn.functional as F
from torchvision import models, transforms

# load the S3 client when lambda execution context is created
s3 = boto3.client('s3')

# classes for the image classification
classes = []

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# get bucket name from ENV variable
MODEL_BUCKET=os.environ.get('MODEL_BUCKET')
logger.info(f'Model Bucket is {MODEL_BUCKET}')

# get bucket prefix from ENV variable
MODEL_KEY=os.environ.get('MODEL_KEY')
logger.info(f'Model Prefix is {MODEL_KEY}')

# processing pipeline to resize, normalize and create tensor object
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def load_model():
    """Loads the PyTorch model into memory from a file on S3.

    Returns
    ------
    Vision model: Module
        Returns the vision PyTorch model to use for inference.

    """
    global classes
    logger.info('Loading model from S3')
    obj = s3.get_object(Bucket=MODEL_BUCKET, Key=MODEL_KEY)
    bytestream = io.BytesIO(obj['Body'].read())
    tar = tarfile.open(fileobj=bytestream, mode="r:gz")
    for member in tar.getmembers():
        if member.name.endswith(".txt"):
            logger.info("Classes file is : %s" % member.name)
            f=tar.extractfile(member)
            classes = f.read().splitlines()
            classes = [c.decode("utf-8") for c in classes]
            logger.info("Classes: %s" % classes)
        if member.name.endswith(".pth"):
            logger.info("Model file is : %s" % member.name)
            f=tar.extractfile(member)
            logger.info("Loading PyTorch model")
            model = torch.jit.load(io.BytesIO(f.read()), map_location=torch.device('cpu')).eval()
    return model

# load the model when lambda execution context is created
model = load_model()

def sort_dict(dic):
    return {k: "%.2f%%"%dic[k] for k in sorted(dic, key=dic.get, reverse=True)}

def predict(input_object, model):
    """Predicts the class from an input image.

    Parameters
    ----------
    input_object: Tensor, required
        The tensor object containing the image pixels reshaped and normalized.

    Returns
    ------
    Response object: dict
        Returns the predicted class and confidence score.

    """
    logger.info("Calling prediction on model")
    start_time = time.time()
    output = model(input_object)
    inference_seconds = float("%.2f"%(time.time() - start_time))
    logger.info("--- Inference time: %s seconds ---" % inference_seconds )
    output_list = [ '%.2f' % float(100*elem) for elem in output[0].detach().numpy()]
    prediction = F.softmax(output, dim=1)
    prediction_list = [ '%.2f' % float(100*elem) for elem in prediction[0].detach().numpy()]
    probabilities=[ '%.2f' % float(100*elem) for elem in prediction[0]]
    response = {}
    temp = list(zip(output_list,prediction_list,probabilities))
    temp2 = dict(zip(classes,temp))
    #print(temp,temp2)
    response['probabilities'] = {k: v for k, v in temp2.items() if float(v[0]) >0}
    response['predictions'] = probabilities
    response['output'] = output_list
    response['summary'] = list(response['probabilities'].keys())
    response['others'] = sort_dict({k: float(v[2]) for k, v in temp2.items() if float(v[0]) <0 and float(v[2]) >0})
    logger.info(f'Predicted class is %s' % response['summary'])

    return response

def base64_to_bytes(base64String):
    image_data = re.sub('^data:image/.+;base64,', '', base64String)
    image_bytes = io.BytesIO(base64.b64decode(image_data))
    return image_bytes

def input_fn(request_body):
    """Pre-processes the input data from JSON to PyTorch Tensor.

    Parameters
    ----------
    request_body: dict, required
        The request body submitted by the client. Expect an entry 'url' containing a URL of an image to classify.

    Returns
    ------
    PyTorch Tensor object: Tensor

    """
    logger.info("Getting input URL to a image Tensor object")
    if isinstance(request_body, str):
        request_body = json.loads(request_body)
    img = PIL.Image.open(base64_to_bytes(request_body['url']))
    img_tensor = preprocess(img)
    img_tensor = img_tensor.unsqueeze(0)
    return img_tensor

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)


def lambda_handler(event, context):
    """Lambda handler function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """
    logger.info("Starting event")
    #log_event = str(event)
    #logger.info((log_event[:100] + '...' + log_event[-100:]) if len(log_event) > 201 else log_event)
    logger.info("Getting input object")
    input_object = input_fn(event['body'])
    logger.info("Calling prediction")
    response = predict(input_object, model)
    logger.info("Returning response: %s" % response)
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(response, cls=MyEncoder)
    }
