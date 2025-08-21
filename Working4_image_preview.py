import streamlit as st
import fitz  # PyMuPDF
import tempfile
import os
import google.generativeai as genai
import openai
import base64

# ==============================
# Sidebar: API & Model Selection
# ==============================
st.sidebar.title("API & Model Settings")

provider = st.sidebar.selectbox("Choose LLM Provider", ["Gemini", "OpenAI"])

api_key = st.sidebar.text_input("Enter your API Key", type="password")

default_model = "gemini-2.5-flash" if provider == "Gemini" else "gpt-4o"
model_name = st.sidebar.text_input("Enter Model Name", value=default_model)

# Global vars for LLM
if "model" not in st.session_state:
    st.session_state.model = None
if "client" not in st.session_state:
    st.session_state.client = None

if st.sidebar.button("Configure API"):
    if api_key:  # configure only if API key entered
        try:
            if provider == "Gemini":
                genai.configure(api_key=api_key)
                st.session_state.model = genai.GenerativeModel(model_name)
                st.session_state.client = None # Ensure client is None if Gemini is selected
                st.sidebar.success("Gemini API configured!")

            elif provider == "OpenAI":
                st.session_state.client = openai.OpenAI(api_key=api_key)
                st.session_state.model = None # Ensure model is None if OpenAI is selected
                st.sidebar.success("OpenAI API configured!")

        except Exception as e:
            st.sidebar.error(f"LLM config error: {e}")
    else:
        st.session_state.model = None
        st.session_state.client = None
        st.sidebar.warning("Please enter an API key.")

# ==============================
# Streamlit Main App
# ==============================
st.title("PDF Chatbot with Drawings & Text")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
        tmp_pdf_file.write(uploaded_file.read())
        tmp_pdf_path = tmp_pdf_file.name

    pdf_document = None
    try:
        pdf_document = fitz.open(tmp_pdf_path)
        st.subheader("PDF Preview")


        image_paths_for_gemini = []
        page_texts = []

        with tempfile.TemporaryDirectory() as tmp_image_dir:
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)

                # High-DPI render for clarity (2x)
                zoom = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=zoom, alpha=False)

                img_filename = f"page_{page_num + 1}.png"
                img_path = os.path.join(tmp_image_dir, img_filename)
                pix.save(img_path)

                # Upload image to Gemini (same as your code)
                uploaded_image = genai.upload_file(img_path)
                image_paths_for_gemini.append(uploaded_image)

                # ALSO grab page text (helps with BOM/title block)
                text = page.get_text("text") or ""
                # limit to avoid token blowup (adjust if needed)
                page_texts.append(text[:6000])

                st.image(img_path, caption=f"Page {page_num + 1}", use_container_width=True)

        # ==============================
        # User Question + Answer
        # ==============================
        question = st.text_input("Ask a question about the PDF (including drawings):")

        if st.button("Get Answer") and question and api_key:
            st.subheader("Answer:")

            if provider == "Gemini" and st.session_state.model:
                system_prompt = (
                    "You are an expert in Engineering Drawing. "
                    "You will be given a technical drawing PDF (converted to images) along with a user's question. "
                    "Use both the text and visual content from the PDF to provide a detailed, accurate, "
                    "and concise answer."
                    "fully examine all pdf pages then only ans a Question"
                    "Check entire pdf file text as well as images then think then only ans"
                    "whatever required ans that only specifically dont give muchh other details"
                    "Generally, the items that have A36 in the “MATERIAL” section of the Bill of Materials if its not there in bill of materials its not there"
                    
                )
                system_prompt += (
                    " Consider ALL pages of the document before answering. "
                    " Cite page numbers for every factual claim (e.g., 'Page 2: ...'). "
                    " If the Bill of Materials (BOM) appears on one page and the title block on another, "
                    " aggregate both. If information conflicts, prefer the most specific/latest revision and say so. "
                    " If an item isn't found on ANY page, answer 'Not found in the provided pages'. "
                    "fully examine all pdf pages then only ans a Question"
                    "Check entire pdf file text as well as images then think then only ans"
                    "whatever required ans that only specifically dont give muchh other details"
                    "(generally, the information for TOOL DESCRIPTION in Title Block/Name Plate)"

"(The plates mentioned as BURNOUT or BO, PLATE in the description of Bill of Materials, quantity mentioned as QTY generally in Bill of Materials)"

"(Generally, the items marked as “X” in the purchase “PUR” section of the Bill of Materials)"

"(Generally, the items marked as “Weldment” in the “DESCRIPTION/ Part Name” section of the Bill of Materials)"

"(Generally, the items marked as “X” in the “PUR” section with supplier name in the “Material” section of the Bill of Materials)"

"(Generally, the purchased items that have been altered, mentioned as (ALTER or ALTERED in description or as a special note in the Bill of Materials)"

"(Generally, the items marked as “SHEETMETAL or LASER/BEND Not only LASER in the “DESCRIPTION/ Part Name” section of the Bill of Materials, if it Only LASER its not sheetmetal item)"

"(Generally, if the description is as “weldment” with some detail number (eg. 2) the corresponding parts of the weldment will have detail numbers as 2A, 2B, 2C… for all the parts ued in that specific weldment)"

"(Generally, these are parts with some values in the “HARD” section of the Bill of Materials)."

"(Generally, the items that have A36 in the “MATERIAL” section of the Bill of Materials)."

"(Generally, the drawn date is mentioned in the “DATE” portion of the TITLE BLOCK/NAME PLATE)"

"(Generally, the scale value is mentioned in the “SCALE” portion of the TITLE BLOCK/NAME PLATE)."
  )

                user_instruction = f"Question: {question}"

                prompt_parts = [
                    system_prompt,
                    f"The PDF has {len(image_paths_for_gemini)} page(s). Review EVERY page before answering.",
                    user_instruction,
                ]

                for idx, (img, txt) in enumerate(zip(image_paths_for_gemini, page_texts), start=1):
                    prompt_parts += [
                        f"== Page {idx} (Image) ==",
                        img,  # keep as your uploaded image object
                        f"== Page {idx} (Extracted Text) ==\n{txt}"
                    ]

                response = st.session_state.model.generate_content(prompt_parts)

                # st.subheader("Answer1:")
                try:
                    if hasattr(response, "text") and response.text:
                        st.write(response.text)
                    elif response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if getattr(part, "text", None):
                                st.write(part.text)
                            else:
                                st.write(part)
                    else:
                        st.write("No text output from Gemini. Please try rephrasing your question.")
                except Exception as e:
                    st.write(f"Parse error: {e}")

            elif provider == "OpenAI" and st.session_state.client:
                system_prompt_openai = (
                    "You are an expert in Engineering Drawing. "
                    "You will be given a technical drawing PDF (converted to images) along with a user's question. "
                    "Use both the text and visual content from the PDF to provide a detailed, accurate, "
                    "and concise answer."
                )
                system_prompt_openai += (
                    " Consider ALL pages of the document before answering. "
                    " Cite page numbers for every factual claim (e.g., 'Page 2: ...'). "
                    " If the Bill of Materials (BOM) appears on one page and the title block on another, "
                    " aggregate both. If information conflicts, prefer the most specific/latest revision and say so. "
                    " If an item isn't found on ANY page, answer 'Not found in the provided pages'. "
                )
                response = st.session_state.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt_openai},
                        {"role": "user", "content": question},
                    ],
                )
                st.write(response.choices[0].message.content)

            else:
                st.error("Please configure API key and model properly.")

    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        if pdf_document:
            pdf_document.close()
