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

# ======== 配置 LLM ========
lm = dspy.LM(
    "openai/qwen2.5vl:72b",
    api_base=OLLAMA_OPENAI_BASE_URL,
    api_key="ollama",
    model_type="chat",
)
dspy.configure(lm=lm)

# ======== 定义 Signature（只输入图片，输出描述） ========
class ImageDescribeSignature(dspy.Signature):
    image: dspy.Image = dspy.InputField(desc="The image to be described")
    description: str = dspy.OutputField(desc="A concise and accurate description of the image content")

# ======== 定义 Module（Predict 模块） ========
image_describer = dspy.Predict(
    signature=ImageDescribeSignature,
    instruction="""
    You are a vision model. Given an image, describe its visible content in one or two sentences.
    Avoid speculation or unrelated commentary.
    """.strip(),
)

# ======== Helper: 将图片转换为 base64 URI ========
def path_to_base64_uri(path: str, fmt: str = "jpg") -> str:
    with open(path, "rb") as f:
        b = f.read()
    return f"data:image/{fmt};base64," + base64.b64encode(b).decode("utf-8").replace("\n", "")

# ======== 调用示例 ========
if __name__ == "__main__":
    image_path = "/data2/jproject/OBQA/sample_data/image_demo/demo2.jpg"

    # 转换为 base64 URI
    uri = path_to_base64_uri(image_path, "jpg")
    img_obj = uri

    # 执行推理
    result = image_describer(image=img_obj)
    print("Description:", result.description)
