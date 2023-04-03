import os
import json
# from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from google.cloud import storage
from google.protobuf.json_format import MessageToJson

project_id = "<your-project-id>"
processor_id = "<your-processor-id>"
location = "<your-processor-location>"
bucket_name = "<your-bucket-name>"
mime_type = 'image/jpeg'


def main(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    bucket = event['bucket']
    file = event
    if ".jpg" in file["name"].lower():
        uri = f"gs://{bucket_name}/{file['name']}"
        data = parse_form(filename = file["name"])

    return "ok"

def parse_form(filename):
    """Parse a form"""
    # opts = ClientOptions()
    client = documentai.DocumentProcessorServiceClient()
    name = client.processor_path(project_id, location, processor_id)

    #get file from gcs
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)

    with blob.open("rb") as f:
        image_content = f.read()

    # Load Binary Data into Document AI RawDocument Object
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    # Configure the process request
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    response = client.process_document(request=request)
    document = response.document

    response_json = type(response).to_json(response)

    # Convert the JSON string to a Python dictionary
    response_dict = json.loads(response_json)


    blob_write = bucket.blob("results/{filename}.json")

    # Write the response result to file 
    with blob_write.open("w") as f:
        json.dump(response_dict, f)

    receipt_data_json = {}

    # Extract form fields
    document_pages = document.pages
    print("Form data detected:\n")
    # For each page fetch each form field and display fieldname, value and confidence scores
    for page in document_pages:
        print("Page Number:{}".format(page.page_number))
        i=1
        for form_field in page.form_fields:
            print("Field no: ", str(i))
            fieldName=get_text(form_field.field_name,document)
            nameConfidence = round(form_field.field_name.confidence,4)
            fieldValue = get_text(form_field.field_value,document)
            valueConfidence = round(form_field.field_value.confidence,4)
            print(fieldName+fieldValue +"  (Confidence Scores: (Name) "+str(nameConfidence)+", (Value) "+str(valueConfidence)+")\n")
            i+=1
            receipt_data_json[fieldName] = str(fieldValue)

    # Define Destination blob object of where the response result will be stored in Bucket
    blob_write = bucket.blob("results/{filename}.json")

    # Write the response result to file in Bucket
    with blob_write.open("w") as f:
        json.dump(receipt_data_json, f)

    return "ok"


def get_text(doc_element: dict, document: dict):
        """
        Document AI identifies form fields by their offsets
        in document text. This function converts offsets
        to text snippets.
        """
        response = ""
        # If a text segment spans several lines, it will
        # be stored in different text segments.
        for segment in doc_element.text_anchor.text_segments:
            start_index = (
                int(segment.start_index)
                if segment in doc_element.text_anchor.text_segments
                else 0
            )
            end_index = int(segment.end_index)
            response += document.text[start_index:end_index]
        return response

