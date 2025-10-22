"""
Use:
cd <project_root>/
conda activate obpaperQA
python dependency/minerUparseDemo/parse_pdf_minerU.py
"""

import requests
import json
import os

url = "http://localhost:8000/file_parse"

def remove_ext_from_fname(fname):
    len_fname = len(fname)
    if len_fname > 4 and fname[-4:] == ".pdf":
        return fname[:-4]
    else:
        return fname

base_data_dir = "sample_data"
input_dir = "sample_data/pdf_doc"
pdf_file = "1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples.pdf"
pdf_file_path = os.path.join(input_dir, pdf_file)
output_path = os.path.join(base_data_dir , "converted_doc")
pdf_name_without_extension = remove_ext_from_fname(pdf_file)

pdf_file2 = "2-Freitas et al. - 2021 - A Large-Scale Database for Graph Representation Learning.pdf"
pdf_file2_path = os.path.join(input_dir, pdf_file2)
output_path2 = os.path.join(base_data_dir , "converted_doc")
pdf_name2_without_extension = remove_ext_from_fname(pdf_file2)

# 文件参数
files = [
    ("files", (pdf_file, open(pdf_file_path, "rb"), "application/pdf")),
    ("files", (pdf_file2, open(pdf_file2_path, "rb"), "application/pdf")),
]


# JSON参数：必须用 "data" + json.dumps()，但字段名应为 "json" 或 "config"，视API文档而定
payload = {
    "output_dir": None,
    "lang_list": ["ch"],
    "backend": "pipeline", # "pipeline" or "vlm-sglang"
    "parse_method": "auto",
    "formula_enable": True,
    "table_enable": True,
    "return_md": True,
    "return_middle_json": False,
    "return_model_output": False,
    "return_content_list": True,
    "return_images": True,
    "response_format_zip": False,
    "start_page_id": 0,
    "end_page_id": 99999,
}

import time
start_time = time.time()
# ✅ 用 "data" 指定 JSON（字段名必须和 API 一致，如 "json" 或 "config"）
response = requests.post(
    url,
    files=files,
    data=payload  # 注意这里是 "json"，不是 "payload"
)
end_time = time.time()
print("Time taken for request: ", end_time - start_time)
print(response.status_code)


result = json.loads(response.text)
res_content = result["results"][pdf_name_without_extension]
print("pdf文件名: " ,pdf_name_without_extension)
res_content_keys = res_content.keys()
print(res_content_keys)

res_content2 = result["results"][pdf_name2_without_extension]
print("pdf文件名: " ,pdf_name2_without_extension)
res_content2_keys = res_content2.keys()
print(res_content2_keys)


save_json_path = os.path.join(output_path, f"{pdf_name_without_extension}_response.json")
with open(save_json_path, "w") as f:
    json.dump(res_content, f, ensure_ascii=False, indent=4)

save_json_path2 = os.path.join(output_path2, f"{pdf_name2_without_extension}_response.json")
with open(save_json_path2, "w") as f:
    json.dump(res_content2, f, ensure_ascii=False, indent=4)
