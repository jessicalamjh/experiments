import glob
import os.path

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, AutoTokenizer, AutoConfig, AutoImageProcessor, GenerationConfig

from postprocessing import extract_classes_bboxes, transform_bbox_to_original, postprocess_text

# Load model and processor
model_path = "nvidia/NVIDIA-Nemotron-Parse-v1.1"  # Or use a local path
device = "cuda:0"

model = AutoModel.from_pretrained(
    model_path,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16
).to(device).eval()
processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)

for filepath in sorted(list(glob.glob(f"data/*.png"))):
    print(f"Current filepath: {filepath}")

    # Load image
    image = Image.open(filepath)

    # Process image
    task_prompt = "</s><s><predict_bbox><predict_classes><output_markdown>"
    inputs = processor(images=[image], text=task_prompt, return_tensors="pt").to(device)
    prompt_ids = processor.tokenizer.encode(task_prompt, return_tensors="pt", add_special_tokens=False).cuda()

    # Generate text
    generation_config = GenerationConfig.from_pretrained(model_path, trust_remote_code=True)
    with torch.no_grad():
        outputs = model.generate(**inputs,  generation_config=generation_config)
    generated_text = processor.batch_decode(outputs, skip_special_tokens=True)[0]

    # Export generated text
    filename = os.path.basename(filepath)
    print(generated_text, file=open(f"output/generated_texts/{filename}", 'w'))

    # Postprocess and re-export
    classes, bboxes, texts = extract_classes_bboxes(generated_text)
    bboxes = [transform_bbox_to_original(bbox, image.width, image.height) for bbox in bboxes]

    # Specify output formats for postprocessing
    table_format = 'markdown' # latex | HTML | markdown
    text_format = 'markdown' # markdown | plain
    blank_text_in_figures = False # remove text inside 'Picture' class
    texts = [postprocess_text(text, cls = cls, table_format=table_format, text_format=text_format, blank_text_in_figures=blank_text_in_figures) for text, cls in zip(texts, classes)]
    
    f_out = open(f"output/markdown/{filename}", 'w')
    for cl, bb, txt in zip(classes, bboxes, texts):
        print(cl, ': ', txt, file=f_out)
    f_out.close()

    print(f"Done with {filepath}\n")
