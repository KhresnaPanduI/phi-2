from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
import os, pickle

MODEL_PATH = r"mistral-7b-instruct-v0.2.Q4_K_M.gguf"

llm = Llama(
    model_path=MODEL_PATH, 
    verbose=True,
    chat_format="llama-2")

llama_history_global = [{"role": "system", "content": "You are helpful assistant."}]


def parse_pdf_to_text(pdf_file):
    if pdf_file is not None:
        pdf_reader = PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text=text)
        
        # create embeddings
        store_name = pdf_file.name[:-4]

        if os.path.exists(f"{store_name}.pkl"):
            with open(f"{store_name}.pkl", "rb") as f:
                VectorStore = pickle.load(f)
        else:
            embeddings = OpenAIEmbeddings()
            VectorStore = FAISS.from_texts(chunks, embedding=embeddings)
            with open(f"{store_name}.pkl", "wb") as f:
                pickle.dump(VectorStore, f)

def gradio_reply(user_input, history, pdf_file=None):
    global llama_history_global

    if pdf_file is not None:
        # Save the PDF to a temporary file
        temp_pdf_path = "/tmp/uploaded.pdf"
        with open(temp_pdf_path, "wb") as temp_pdf:
            temp_pdf.write(pdf_file["content"])
        
        # Parse PDF and create embeddings
        user_input = parse_pdf_and_create_embeddings(temp_pdf_path)

    # Append the user's input to Llama history
    llama_history_global.append({"role": "user", "content": f"{user_input} answer concisely"})
    response = llm.create_chat_completion(messages=llama_history_global)
    assistant_response = response['choices'][0]['message']['content']

    history.append((user_input, assistant_response))
    llama_history_global.append({"role": "assistant", "content": assistant_response})

    return "", history

with gr.Blocks() as interface:
    with gr.Row():
        message = gr.Textbox(label="Type your message or upload a PDF:", placeholder="Type here or upload a PDF below")
        pdf_upload = gr.File(label="Or upload a PDF", type="pdf", clearable=True)
    chatbot = gr.Chatbot(height=600)
    submit_btn = gr.Button("Submit")
    clear = gr.ClearButton([message, chatbot, pdf_upload])
    submit_btn.click(gradio_reply, [message, chatbot, pdf_upload], [message, chatbot])

if __name__ == "__main__":
    interface.launch()