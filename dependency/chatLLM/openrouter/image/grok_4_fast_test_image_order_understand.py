import base64
from openai import OpenAI

# ==========================
# 🔧 配置你的本地图像路径
# ==========================
IMG1_PATH = "/data2/jproject/OBQA/sample_data/images/dog.png"   # ← 请替换
IMG2_PATH = "/data2/jproject/OBQA/sample_data/images/cat.png"   # ← 请替换

# ==========================
# 🔧 base64 编码函数
# ==========================
def encode_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

img1_b64 = encode_base64(IMG1_PATH)
img2_b64 = encode_base64(IMG2_PATH)

# ==========================
# 🔧 OpenAI / OpenRouter Client
# ==========================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# ==========================
# 🔥 Prompt：测试模型是否理解顺序
# ==========================
prompt_text = """
You will receive two images in the exact order below:

- Image 1 is the *first* image.
- Image 2 is the *second* image.

Please answer:

1. What animal is in Image 1?
2. What animal is in Image 2?

Answer clearly as:
Image 1: ...
Image 2: ...
"""

# ==========================
# 🔥 构建消息（两张图片按顺序传入）
# ==========================
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img1_b64}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img2_b64}"}},
        ],
    }
]

# ==========================
# 🔥 模型推理
# ==========================
resp = client.chat.completions.create(
    model="x-ai/grok-4-fast",
    messages=messages,
)

print(resp.choices[0].message.content)
