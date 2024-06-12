import os
import PyPDF2
import sys

# set parameters from command line
pdf_folder_path = sys.argv[1] 
model = sys.argv[2] 
instruction_pre = open(sys.argv[3],'r').read()
instruction_post = open(sys.argv[4],'r').read()
outfile_name =  sys.argv[5] 

# get files in folder
pdf_names = os.listdir(pdf_folder_path)
pdf_addresses = list(map(lambda pdf: pdf_folder_path + '/' + pdf,pdf_names))

# function to read the a pdf and extract the text inside
def extract_text_from_pdf(file_path):
    print(file_path)
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
    if text == '':
        text = 'This pdf file failed to be transformed into text!'
    return text

# apply the function to all pdfs in pdf_folder_path using their pdf_address
## OBS! An error may occur if the pdf file name is too long!! Rename the file and try again
pdf_list = [extract_text_from_pdf(pdf_address) for pdf_address in pdf_addresses]


from openai import OpenAI
client = OpenAI()


# The function takes the information set above to formulate the prompt and, ultimately, the request using the information set above:
# model = openai model (e.g. gpt-4-turbo)
# instruction_pre is read from txt file 
# the text = pdf_text
# instruction_post is read from txt file

def analyze_text_with_gpt(model,instruction_pre,instruction_post,text,text_name):

    print("calling LLM for " + text_name)
    response = client.chat.completions.create(
        model= model,
        messages=[
            {"role": "system", "content": "pre_article_guidelines: {" + instruction_pre + "}"},
            {"role": "system", "content": "scientific_article_document_text: {" + text + "}"},
            {"role": "system", "content": "post_article_completion_task: {" + instruction_post + "}"},
        ],
        temperature = 0,
        #OBS! According to the openai documentation, the json format needs to be specified both in the prompt and the request under response_format
        response_format= { "type": "json_object" }
    )

    import json
    # append the filename before the
    file = json.dumps(
        {'filename': text_name,
         'response': json.loads(response.choices[0].message.content)}
    )
    return file

output_data = [analyze_text_with_gpt(model,instruction_pre, instruction_post,pdf,pdf_name) for pdf,pdf_name in zip(pdf_list,pdf_names)]



with open(outfile_name,'w') as outfile:
    # json.dump doesn't get this right because the output from the gpt is a string of json txt, not an object
    outfile.write("["+",".join(output_data)+"]")
# print(data)
outfile.close()
