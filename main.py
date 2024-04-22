from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from typing import List, Optional
import json
import google.generativeai as genai
import fitz
from io import BytesIO
import os
import io 

app: FastAPI = FastAPI(title="DemanualAI-Invoice_parser", version="0.2.0")

# Configure CORS middleware
origins = ["*"]  # All origins are allowed, you may adjust this based on your needs
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key="AIzaSyA8uO3_RA3jSOMWHIhYj0Lvv6TUKqKqZHQ")
model = genai.GenerativeModel('gemini-pro-vision')

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

# Define the bill items to be tracked
BILL_ITEMS = [
    "invoice_number",
    "invoice_date",
    "total_tax",
    "invoice_amount",
    "Items purchased",
    "buyer_name/Consignee",
    "buyer_address",
    "buyer_phone_number",
    "seller_name",
    "seller_address",
    "seller_phone_number"
]

# def pdf_to_pil(pdf_bytes: bytes) -> Image.Image:
#     # Convert first page of PDF to PIL image
#     doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#     page = doc.load_page(0)  # Load first page
#     pixmap = page.get_pixmap()
#     img = Image.open(BytesIO(pixmap.tobytes()))

#     # Resize image if it exceeds 1000x1000 pixels while maintaining aspect ratio
#     max_size = 1000
#     width, height = img.size
#     if width > max_size or height > max_size:
#         ratio = min(max_size / width, max_size / height)
#         new_width = int(width * ratio)
#         new_height = int(height * ratio)
#         img = img.resize((new_width, new_height))

#     doc.close()
#     return img

def pdf_to_pil(pdf_bytes: bytes) -> Image.Image:
    # Convert all pages of PDF to a single PIL image stitched vertically
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = 4
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pixmap = page.get_pixmap(matrix=mat)
        img = Image.open(BytesIO(pixmap.tobytes()))
        images.append(img)

    # Combine images vertically
    total_height = sum(img.size[1] for img in images)
    max_width = max(img.size[0] for img in images)
    combined_img = Image.new('RGB', (max_width, total_height))
    y_offset = 0
    for img in images:
        combined_img.paste(img, (0, y_offset))
        y_offset += img.size[1]
        
    # Create directory if it doesn't exist
    os.makedirs('save_folder', exist_ok=True)

    # Save the combined image
    save_path = os.path.join('save_folder', "stitched_image.jpg")
    combined_img.save(save_path, quality=100)

    doc.close()
    return combined_img

@app.post("/parse_invoice/")
async def parse_invoice(
    file: UploadFile = File(...), 
    tracked_items: Optional[List[str]] = None
):
    if file.filename.endswith('.pdf'):
        pdf_bytes = await file.read()
        pil_images = pdf_to_pil(pdf_bytes)
        image = pil_images
    else:
        image = Image.open(file.file)

    response = model.generate_content([f"""Extract specific information from the invoice image attached and give the response as a JSON. Specific information needed in json response are: {BILL_ITEMS}. Make sure the response json only has the keys that are needed and nothing else. 
    To remember :For total tax, there might be multiple taxes in a single invoices for example CGST and SGST, remember to add them for actual output of total taxes.
    For Invoice number, it can also contain characters for example, 001, KJL0901, JK-098-VGH all are valid invoice/bill numbers. 
    For buyer_address and seller_address, Make sure only to return the full address and strictly do not add details like pan number, phone number, and gst number in the result. Also check if a valid address is given if not return null.
    For buyer_phone_number and seller_phone_number, Most of the times it is linked with their respective addresses.
    """,image], safety_settings=safety_settings, generation_config=generation_config)     
    response_text=response.text 
    start_index = response_text.find('{')
    end_index = response_text.rfind('}') + 1
    invoice_info = json.loads(response_text[start_index:end_index])
    return invoice_info

import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def extract_text_from_image(image) -> list:
    text = pytesseract.image_to_string(image)
    text_list = text.splitlines()
    return text_list

@app.post("/parse_invoice_ocr/")
async def parse_invoice_ocr(
    file: UploadFile = File(...), 
    tracked_items: Optional[List[str]] = None
):
    if file.filename.endswith('.pdf'):
        pdf_bytes = await file.read()
        pil_images = pdf_to_pil(pdf_bytes)
        image = pil_images
    else:
        image = Image.open(file.file)

    text_list = extract_text_from_image(image)

    # Generate content using generative model
    response = model.generate_content([
        f"""Extract specific information from the invoice image attached and give the response as a JSON. Specific information needed in json response are: {BILL_ITEMS}.
        {text_list} are the list original text in the image extracted through ocr so that you will not mke mistakes in responding with random text which are not in the image, and I want you to match your result with the list and provide the response with corrected spellings words.
        The response should be a JSON consists of {BILL_ITEMS}.
        For total_tax, make sure to dd the taxes if there re multiple taxes like and sgst, cgst
       For buyer_address and seller_address, Make sure only to return the full address and strictly do not add details like pan number, phone number, and gst number in the result. Also check if a valid address is given if not return null.
        For buyer_phone_number and seller_phone_number, Most of the times it is linked with their respective addresses.
        """, image
    ], safety_settings=safety_settings, generation_config=generation_config)

    # Extracting JSON from the response
    response_text = response.text 
    start_index = response_text.find('{')
    end_index = response_text.rfind('}') + 1
    invoice_info = json.loads(response_text[start_index:end_index])
    return invoice_info

# @app.post("/parse_invoice_ocr/")
# async def parse_invoice_ocr(
#     file: UploadFile = File(...), 
#     tracked_items: Optional[List[str]] = None
# ):
#     if file.filename.endswith('.pdf'):
#         pdf_bytes = await file.read()
#         pil_images = pdf_to_pil(pdf_bytes)
#         image = pil_images
#     else:
#         image = Image.open(file.file)

#     # Convert PIL Image to bytes
#     with io.BytesIO() as output:
#         # Convert the image to RGB mode
#         image = image.convert("RGB")
#         image.save(output, format="JPEG")
#         image_bytes = output.getvalue()

#     # Perform OCR to extract text from the image
#     result = reader.readtext(np.array(image))

#     # Extract text from the result
#     text_in_images = [detection[1] for detection in result]

#     # Generate content using generative model
#     response = model.generate_content([f"""Extract specific information from the invoice image attached and give the response as a JSON. Specific information needed in json response are: {BILL_ITEMS}.
#     {text_in_images} are the original text in the image and I want you to match your result with the list and provide the response with corrected spellings words.
#     The response should be a a json consists of{BILL_ITEMS}.
#     """, image], safety_settings=safety_settings, generation_config=generation_config)     
#     response_text = response.text 
#     start_index = response_text.find('{')
#     end_index = response_text.rfind('}') + 1
#     invoice_info = json.loads(response_text[start_index:end_index])
#     return invoice_info
