# -*- coding: utf-8 -*-
import base64
from PIL import Image
import dspy

# ======== 配置你的 LLM ========
lm = dspy.LM(
    "ollama_chat/qwen2.5vl:72b",
    api_base="http://localhost:11434/v1",
    api_key="",       # 根据你的设置
    model_type="chat"
)
dspy.configure(lm=lm)

# ======== 定义 Signature （输入包括图片 + 文本） ========
class ImageQASignature(dspy.Signature):
    image: dspy.Image = dspy.InputField(desc="The image to be described")
    question: str = dspy.InputField(desc="A question about the image")
    answer: str = dspy.OutputField(desc="The answer returned by the model")

# ======== 定义 Module（Predictor） ========
# 选择最简单的 Predict 模块（你也可用 ChainOfThought 等）
qa_model = dspy.Predict(
    signature=ImageQASignature,
    instruction="""
    Given an image and a question about it, answer the question in a concise sentence.
    """.strip()
)

# ======== Helper: 从文件生成 base64 或直接用 PIL/bytes ========
def path_to_base64_uri(path: str) -> str:
    with open(path, "rb") as f:
        b = f.read()
    return "data:image/jpeg;base64," + base64.b64encode(b).decode("utf-8")

# ======== 调用示例 ========
if __name__ == "__main__":
    image_path = "/data2/jproject/OBQA/sample_data/image_demo/demo1.jpg"
    # 方法 A：直接传文件路径／PIL
    img_obj = dspy.Image(image_path)
    # 或 方法 B：如果你已经有 base64 uri
    # uri = path_to_base64_uri(image_path)
    # img_obj = dspy.Image(uri)
    # 或 方法 C：如果你有 raw bytes:
    # with open(image_path, "rb") as f:
    #     img_bytes = f.read()
    # img_obj = dspy.Image(img_bytes)

    q = "What is shown in this image? Describe it in one sentence."

    result = qa_model(image=img_obj, question=q)
    print("Answer:", result.answer)
