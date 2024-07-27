from fastapi import FastAPI, File, UploadFile, APIRouter, Response,  Request
from PIL import Image
from typing import List, Optional
import json
import google.generativeai as genai
import fitz
from io import BytesIO
import os
import io 
import pytesseract
import base64

app = FastAPI()

genai.configure(api_key="AIzaSyA7qBvXge6Ss6_D8SMAK982C1cT3ZfZgjM")
model = genai.GenerativeModel('gemini-1.5-flash') 

generation_config = {
    "temperature": 0.1
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_DANGEROUS",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]

BILL_ITEMSS = [
    "VIN/Chassis Number",
    "Registration Mark",
    "Engine Number",
    "Make",
    "Model",
    "Model Number",
    "Colour",
    "Vehicle Category",
    "Propelled By",
    "Net Weight",
    "GVM kg",
    "Class",
    "Engine Capacity",
    "Seating Capacity",
    "Registration Authority",
    "Year Of Make",
    "First Registration Date",
    "Customs Clearance Number",
    "Interpol Number"
]

router = APIRouter()

def pdf_to_pil(pdf_bytes: bytes) -> Image.Image:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = 4
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pixmap = page.get_pixmap(matrix=mat)
        img = Image.open(BytesIO(pixmap.tobytes()))
        images.append(img)

    total_height = sum(img.size[1] for img in images)
    max_width = max(img.size[0] for img in images)
    combined_img = Image.new('RGB', (max_width, total_height))
    y_offset = 0
    for img in images:
        combined_img.paste(img, (0, y_offset))
        y_offset += img.size[1]
        
    os.makedirs('save_folder', exist_ok=True)
    
    save_path = os.path.join('save_folder', "stitched_image.jpg")
    combined_img.save(save_path, quality=100)

    doc.close()
    return combined_img

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


def extract_text_from_image(image) -> list:
    text = pytesseract.image_to_string(image)
    text_list = text.splitlines()
    return text_list

@router.post("/parse_user_vehicle_info/")
async def parse_user_vehicle_info(file: UploadFile = File(...),):
    if file.filename.endswith('.pdf'):
        pdf_bytes = await file.read()
        pil_images = pdf_to_pil(pdf_bytes)
        image = pil_images
    else:
        image = Image.open(file.file)

    text_list = extract_text_from_image(image)
    print(text_list)
    response = model.generate_content([f"""
    Extract and verify user and vehicle information from the provided document.
    The text extracted via OCR is: {text_list}
    Please extract and verify the following information:
    {BILL_ITEMSS}
    For Seating capacity, it can also contain numerical characters for example, 01 or 1 all are valid seat capacity. 
    Provide the response as a JSON object with these fields.
    If any information is missing or cannot be verified, set the value to null.
    example:
    Customs Clearance Number:null
    Interpol Number:123
    """, image], safety_settings=safety_settings, generation_config=generation_config)

    response_text = response.text
    start_index = response_text.find('{')
    end_index = response_text.rfind('}') + 1
    user_vehicle_info = json.loads(response_text[start_index:end_index])
    return user_vehicle_info


# @router.post("/parse_invoice_ocr/")
# async def parse_invoice_ocr(file: UploadFile = File(...)):
#     file_bytes = await file.read()
#     file_base64 = base64.b64encode(file_bytes).decode('utf-8')

#     try:
#         response = model.generate_content([
#             f"""
#             You are an expert in extracting and verifying information from vehicle documents.
#             The document content (in base64) is: {file_base64}
#             The document may be unclear or noisy. Please handle this accordingly.
#             Extract and verify the following information, and ensure the data is as accurate as possible:
#             {BILL_ITEMSS}
#             Provide the response as a JSON object with these fields.
#             Look at the file information carefully; do not miss the values.
#             If any information is missing or cannot be verified, set the value to null.
#             Example:
#             {{
#                 "Customs Clearance Number": null,
#                 "Interpol Number": "123",
#                 "VIN/Chassis Number": "1HGCM82633A123456",
#                 "Registration Mark": "ABC1234",
#                 "Engine Number": "E1234567",
#                 "Make": "Toyota",
#                 "Model": "Corolla",
#                 "Model Number": "2010",
#                 "Colour": "Blue",
#                 "Vehicle Category": "Sedan",
#                 "Propelled By": "Gasoline",
#                 "Net Weight": "1300 kg",
#                 "GVM kg": "1500 kg",
#                 "Class": "Private",
#                 "Engine Capacity": "1800 cc",
#                 "Seating Capacity": "5",
#                 "Registration Authority": "DMV",
#                 "Year Of Make": "2010",
#                 "First Registration Date": "2022-01-01",
#                 "Customs Clearance Number": null,
#                 "Interpol Number": null
#             }}
#             """,
#         ], safety_settings=safety_settings, generation_config=generation_config)

#         response_text = response.text 
#         start_index = response_text.find('{')
#         end_index = response_text.rfind('}') + 1
        
#         if start_index == -1 or end_index == -1:
#             raise ValueError("No JSON object found in the response.")

#         invoice_info = json.loads(response_text[start_index:end_index])
#         return invoice_info

#     except Exception as e:
#         return {"error": str(e)}
