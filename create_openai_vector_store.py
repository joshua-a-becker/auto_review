import sys
import os
from openai import OpenAI

openAI_key = sys.argv[1]
pdf_folder_path = sys.argv[2]
vector_store_name = sys.argv[3]

# Get the pdfs from the designated folder
pdf_names = os.listdir(pdf_folder_path)
pdf_addresses = list(map(lambda pdf: pdf_folder_path + '/' + pdf,pdf_names))

# Open an openai client
client = OpenAI(api_key=openAI_key)
# Create a vector store (e.g., "Research Papers")
vector_store = client.beta.vector_stores.create(name=vector_store_name)
client.beta.vector_stores
# Ready the files for upload to OpenAI
file_paths = pdf_addresses[1:3]
file_streams = [open(path, "rb") for path in file_paths]

# Use the upload and poll SDK helper to upload the files, add them to the vector store,
# and poll the status of the file batch for completion.
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)
 
# You can print the status and the file counts of the batch to see the result of this operation.
print(file_batch.status)
print(file_batch.file_counts)

with open("vector_store_id.txt", "wb") as f:
    f.write(vector_store.id)

