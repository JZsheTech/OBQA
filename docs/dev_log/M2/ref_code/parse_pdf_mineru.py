import os
import json
import requests
import time
import debugpy



def parse_pdf_with_mineru(pdf_path: str, pdf_file_name: str, 
                          url: str = "http://localhost:18543/file_parse",
                          lang_list=None, backend="pipeline", return_md=True,  return_images=False, return_content_list=False) -> dict:
    """
    调用本地 MinerU 服务解析 PDF 文件，并返回 res_content JSON。

    Args:
        pdf_path (str): PDF 文件所在目录路径。
        pdf_file_name (str): PDF 文件名（带 .pdf 后缀）。
        url (str): MinerU 服务地址，默认 http://localhost:18543/file_parse。
        lang_list (list): 语言列表，默认为 ["ch"]。

    Returns:
        dict: MinerU 返回结果中对应 pdf 的 res_content JSON。
        返回字段: ['md_content', 'content_list', 'images']
    """

    def remove_ext(fname: str):
        return fname[:-4] if fname.lower().endswith(".pdf") else fname

    pdf_file_path = os.path.join(pdf_path, pdf_file_name)
    pdf_name_noext = remove_ext(pdf_file_name)

    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"❌ 文件不存在: {pdf_file_path}")

    # 构造上传文件字段
    files = [("files", (pdf_file_name, open(pdf_file_path, "rb"), "application/pdf"))]

    # 请求参数
    payload = {
        "output_dir": None,
        "lang_list": lang_list or ["ch"],
        "backend": backend,
        "parse_method": "auto",
        "formula_enable": True,
        "table_enable": True,
        "return_md": return_md,
        "return_middle_json": False,
        "return_model_output": False,
        "return_content_list": return_content_list,
        "return_images": return_images,
        "response_format_zip": False,
        "start_page_id": 0,
        "end_page_id": 99999,
    }

    start_time = time.time()
    response = requests.post(url, files=files, data=payload)
    elapsed = time.time() - start_time

    print(f"[MinerU] ✅ 请求完成，用时 {elapsed:.2f}s, 状态码 {response.status_code}")

    if response.status_code != 200:
        raise RuntimeError(f"❌ MinerU 请求失败: {response.status_code}, 内容: {response.text[:500]}")

    result = json.loads(response.text)
    if "results" not in result or pdf_name_noext not in result["results"]:
        raise KeyError(f"❌ 结果中未找到 {pdf_name_noext} 对应内容")

    res_content = result["results"][pdf_name_noext]
    print(f"[MinerU] 解析成功: {pdf_name_noext}, 返回字段: {list(res_content.keys())}")
    return res_content


# 示例用法：
if __name__ == "__main__":
    # base_dir = "/data/QUEST/jzshe/project/quest/data_link/docs/pdf-doc"
    base_dir = "/home/zhangzihao/hjy/quest/ldu_test/pdf"
    # pdf_file = "5-Wu et al. - 2022 - HQANN Efficient and Robust Similarity Search for .pdf"
    pdf_file = "4091930.pdf"
    result_json = parse_pdf_with_mineru(base_dir, pdf_file)
    data = json.loads(result_json['content_list'])
    for item in data:
        print(item)
    # print(json.dumps(result_json, indent=2, ensure_ascii=False)[:500])
