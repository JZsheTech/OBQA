# -*- coding: utf-8 -*-
import base64
import os
import sys
from pathlib import Path

from PIL import Image
import dspy


def _ensure_repo_root_on_path() -> None:
    """Ensure EviQAsys settings remain importable for direct script execution."""
    repo_root = None
    for parent in Path(__file__).resolve().parents:
        if (parent / "EviQAsys").exists():
            repo_root = parent
            break
    if repo_root is not None and str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))


_ensure_repo_root_on_path()

try:
    from EviQAsys.backend.app.env_setting import OLLAMA_OPENAI_BASE_URL
except (ModuleNotFoundError, ImportError):
    def _default_ollama_openai_base_url() -> str:
        protocol = os.getenv("OLLAMA_PROTOCOL", "http")
        host = os.getenv("OLLAMA_HOST", "localhost")
        port = os.getenv("OLLAMA_PORT", "11434")
        base_url = os.getenv("OLLAMA_BASE_URL", f"{protocol}://{host}:{port}")
        return os.getenv("OLLAMA_OPENAI_BASE_URL", f"{base_url}/v1")

    OLLAMA_OPENAI_BASE_URL = _default_ollama_openai_base_url()

# ======== 配置你的 LLM ========
lm = dspy.LM(
    "openai/qwen2.5vl:72b",
    api_base=OLLAMA_OPENAI_BASE_URL,
    api_key="ollama",       # 根据你的设置
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
    image_path = "/data2/jproject/OBQA/sample_data/image_demo/demo2.jpg" # 一个损失函数的公式

    # 方法 A：直接传文件路径／PIL
    img_obj = image_path
    # 或 方法 B：如果你已经有 base64 uri
    # uri = path_to_base64_uri(image_path)
    # img_obj = uri
    # 或 方法 C：如果你有 raw bytes:
    # with open(image_path, "rb") as f:
    #     img_bytes = f.read()
    # img_obj = img_bytes

    q = "Describe the image"

    result = qa_model(image=img_obj, question=q)
    print("Answer:", result.answer)
