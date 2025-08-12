import streamlit as st

import fitz # PyMuPDF
import tempfile
import os
import google.generativeai as genai

# API key configuration (recommended to use environment variable in production)
GEMINI_API_KEY = "AIzaSyDqmc4WlH8tGTuJKoun4fyzl17Q98AkU60"
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-pro")

st.title("PDF Chatbot with Drawings & Text (Gemini Multimodal)")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
        tmp_pdf_file.write(uploaded_file.read())
        tmp_pdf_path = tmp_pdf_file.name

    pdf_document = None
    try:
        pdf_document = fitz.open(tmp_pdf_path)
        st.subheader("Preview PDF Pages as Images:")
        image_paths_for_gemini = []

        with tempfile.TemporaryDirectory() as tmp_image_dir:
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap()
                img_filename = f"page_{page_num + 1}.png"
                img_path = os.path.join(tmp_image_dir, img_filename)
                pix.save(img_path)

                uploaded_image = genai.upload_file(img_path)
                image_paths_for_gemini.append(uploaded_image)

                st.image(img_path, caption=f"Page {page_num + 1}", use_column_width=True)

            question = st.text_input("Ask a question about the PDF (including drawings):")

            if st.button("Get Answer") and question:
                # Prompt Engineering block
                system_prompt = (
                    "You are an expert in Engineering Drawing. "
                    "You will be given a technical drawing PDF (converted to images) along with a user's question. "
                    "Use both the text and visual content from the PDF to provide a detailed, accurate, "
                    "and concise answer. If the question refers to a diagram, describe the diagram "
                    "and relate it to the question. Answer in English, "
                    
					"List down number of burnout plates used in assembly along with quantities. (The plates mentioned as BURNOUT or BO, PLATE in the description of Bill of Materials, quantity mentioned as QTY generally in Bill of Materials),List down the purchased items used in assembly. (Generally, the items marked as “X” in the purchase “PUR” section of the Bill of Materials),List down the weldments used in assembly. (Generally, the items marked as “Weldment” in the “DESCRIPTION/ Part Name” section of the Bill of Materials),List down the purchased items used in assembly supplied by RENTAPEN. (Generally, the items marked as “X” in the “PUR” section with supplier name in the “Material” section of the Bill of Materials),List down the purchased altered items used in assembly. (Generally, the purchased items that have been altered, mentioned as (ALTER or ALTERED in description or as a special note in the Bill of Materials),List down the sheetmetal items used in assembly. (Generally, the items marked as “SHEETMETAL or LASER/BEND Not Only LASER” in the “DESCRIPTION/ Part Name” section of the Bill of Materials),List down the weldments along with the corresponding individual parts used in the assembly. (Generally, if the description is as “weldment” with some detail number (eg. 2) the corresponding parts of the weldment will have detail numbers as 2A, 2B, 2C… for all the parts ued in that specific weldment), What are the parts with specific surface treatment or hardness used in the assembly? (Generally, these are parts with some values in the “HARD” section of the Bill of Materials),List down the parts that have material “A36”. (Generally, the items that have A36 in the “MATERIAL” section of the Bill of Materials),What is the date on which the drawing has been made? (Generally, the drawn date is mentioned in the “DATE” portion of the TITLE BLOCK/NAME PLATE),What is the scale used for the drawing? (Generally, the scale value is mentioned in the “SCALE” portion of the TITLE BLOCK/NAME PLATE). (Example of title block below)"

                )

                user_instruction = f"Question: {question}\nAnswer step-by-step with clarity."

                # Prepare prompt parts
                prompt_parts = [system_prompt, user_instruction] + image_paths_for_gemini

                # Generate response
                response = model.generate_content(prompt_parts)

                st.subheader("Answer:")
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.text:
                            st.write(part.text)
                        else:
                            st.write(part)
                else:
                    st.write("No text output from Gemini. Please try rephrasing your question.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        if pdf_document:
            pdf_document.close()