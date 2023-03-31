from slack.signature import SignatureVerifier
from google.cloud import storage
from slack_sdk import WebClient
import logging, os, io
import ssl, certifi 
import requests
import shutil
import wget
import uuid


# Initialize the Web API client
# This expects that you've already set your SLACK_BOT_TOKEN as an environment variable
# Try to resist the urge to put your token directly in your code, as it is best practice not to.
# An ssl.SSLContext instance, helpful for specifying your own custom certificate chain
ssl_context = ssl.create_default_context(cafile=certifi.where())
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'], ssl=ssl_context)

# Tests to see if the token is valid
auth_test = client.auth_test()
bot_user_id = auth_test["user_id"]
print(f"App's bot user: {bot_user_id}")


# [START functions_verify_webhook]
def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ['SLACK_SECRET'])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError('Invalid request/credentials.')
    # else:
    #     print("Signature verified")
# [END functions_verify_webhook]


def slack_events(request):
    if request.headers["Content-Type"] == "application/json":
        # verify_signature(request)
        event_data = request.get_json()
        print("Request received")

        if "challenge" in event_data:
            return event_data["challenge"]
        if "event" in event_data and event_data["event"]["type"] == "file_shared":
            handle_image(event_data["event"])

    return f"OK"

def handle_image(event):
    file_id = event['file_id']
    print("file received: ", file_id)
    try:
        file_info = client.files_info(file=file_id)
        print("file info: ", file_info)

        if 'image' in file_info['file']['mimetype']:
            file_url = file_info['file']['url_private']
            response = requests.get(file_url)
            file_name = "/tmp/tmp_doc.jpg"
            destination_name = "{}.jpg".format(str(uuid.uuid4()))
            upload_blob(file_url, file_name, destination_name)

        elif 'application/pdf' in file_info['file']['mimetype']:
            file_url = file_info['file']['url_private']
            response = requests.get(file_url)
            file_name = "/tmp/tmp_doc.pdf"
            destination_name = "{}.pdf".format(str(uuid.uuid4()))
            upload_blob(file_url, file_name, destination_name)

    except Exception as e:
        print("Error fetching file info: {}".format(e))

def upload_blob(URL, file_name, destination_name):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    token = os.environ['SLACK_BOT_TOKEN']
    res = requests.get(URL, stream = True, headers={'Authorization': 'Bearer %s' % token})


    if res.status_code == 200:
        with open(file_name,'wb') as f:
            shutil.copyfileobj(res.raw, f)
        print('File sucessfully Downloaded: ',file_name)
    else:
        print('File Couldn\'t be retrieved')

    destination_blob_name = "receipts/" + destination_name
    storage_client = storage.Client()
    bucket = storage_client.bucket("slack_documents")
    blob = bucket.blob(destination_blob_name)
    source_file_name = file_name

    blob.upload_from_filename(source_file_name)

    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )
