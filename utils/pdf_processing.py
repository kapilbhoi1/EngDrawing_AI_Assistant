import os
from pdf2image import convert_from_path

def pdf_to_images(pdf_path,output_folder="data/images"):
    os.makedirs(output_folder,exist_ok=True)
    images = convert_from_path(pdf_path,dpi=300)
    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(output_folder,f"page_{i+1}.png")
        img.save(img_path,"PNG")
        image_paths.append(img_path)
    return image_paths    