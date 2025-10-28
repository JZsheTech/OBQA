
import dashscope
import os
import base64
import json
from http import HTTPStatus

# 输入数据
input = [{'text': 'A math equation described the training process of a neural network.'}]

os.environ['DASHSCOPE_API_KEY'] = 'sk-aa5f15008e5b420bbcbaf822bb782718'  # 请替换为您的DashScope API Key

# 调用模型接口
resp = dashscope.MultiModalEmbedding.call(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    model="qwen2.5-vl-embedding",
    input=input
)

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
    print("num of embeddings: ", len(resp.output["embeddings"]))
else:
    print(resp)

# resp.output["embeddings"][0]["embedding"] 
# 类型 ： list[float]