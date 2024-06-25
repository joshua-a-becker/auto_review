import sys
from openai import OpenAI

openAI_key = sys.argv[1]
openai_model = sys.argv[2]
assistant_instruction = sys.argv[3]
vector_store_id = open("vector_store_id.txt","r").readline()
user_submission = open("tasks",'r').readlines()

# Open an openai client
client = OpenAI(api_key=openAI_key)
# Create an assistant
assistant = client.beta.assistants.create(
  name="Research Assistant",
  description = assistant_instruction, # e.g., 'You are a really good research assistant whose primary role is to accurately extract and summarise information from scientific articles for literature review purposes'
  model= openai_model,#"gpt-4o",
  tools=[{"type": "file_search"}],
)
# Set up the assistant to use the vector store we created
assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
)

# Get the file id for each paper in the vector store as we may want to apply the message for each file
v_files=client.beta.vector_stores.files.list(vector_store_id=vector_store_id)
file_ids=[v_files.data[i].id for i in range(len(v_files.data))]

## Threading
# Create a thread and attach the file to the message
thread = client.beta.threads.create(
  messages=[{"role": "user", "content": x,"attachments": [{ "file_id": y, "tools": [{"type": "file_search"}]}]} for y in file_ids for x in user_submission]
)

# Use the create and poll SDK helper to create a run and poll the status of
# the run until it's in a terminal state.

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

message_content = messages[0].content[0].text
annotations = message_content.annotations
citations = []
for index, annotation in enumerate(annotations):
    message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
    if file_citation := getattr(annotation, "file_citation", None):
        cited_file = client.files.retrieve(file_citation.file_id)
        citations.append(f"[{index}] {cited_file.filename}")

print(message_content.value)
print("\n".join(citations))