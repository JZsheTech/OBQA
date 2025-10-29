import dashscope
import os
import base64
import json
from http import HTTPStatus
# 读取图片并转换为Base64,实际使用中请将xxx.png替换为您的图片文件名或路径
image_path = "sample_data/image_demo/demo1.jpg"
with open(image_path, "rb") as image_file:
    # 读取文件并转换为Base64
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
# 设置图像格式
image_format = "jpg"  # 根据实际情况修改，比如jpg、bmp 等
image_data = f"data:image/{image_format};base64,{base64_image}"
# 输入数据
input = [{'image': image_data}]

os.environ['DASHSCOPE_API_KEY'] = 'sk-aa5f15008e5b420bbcbaf822bb782718'  # 请替换为您的DashScope API Key

# 调用模型接口
resp = dashscope.MultiModalEmbedding.call(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="multimodal-embedding-v1",
    input=input
)
# multimodal-embedding-v1 , "qwen2.5-vl-embedding"
# multimodal-embedding-v1是免费的， 其实就是模型gme-qwen2-vl-2b-instruct

if resp.status_code == HTTPStatus.OK:
    result = {
        "status_code": resp.status_code,
        "request_id": getattr(resp, "request_id", ""),
        "code": getattr(resp, "code", ""),
        "message": getattr(resp, "message", ""),
        "output": resp.output,
        "usage": resp.usage
    }
    print(json.dumps(result, ensure_ascii=False, indent=4))
else:
    print(resp)

# resp.output["embeddings"][0]["embedding"] 
# 类型 ： list[float]