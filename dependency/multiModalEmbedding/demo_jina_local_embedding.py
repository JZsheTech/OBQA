# -*- coding: utf-8 -*-
"""
Looped requests demo for Jina Embeddings v4 served via vLLM API
- Use message-style input
- Each request returns exactly ONE embedding
- We loop 4 times to get: {text}, {text+text}, {text+image}, {image}
Author: Jim Sutton
"""

import base64
import requests
from typing import List, Dict, Any, Optional


# ==========================================================
# 工具函数：将图片转成 base64 URL
# ==========================================================
def image_to_base64_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")
    # 你也可以根据图片后缀改成 image/jpeg
    return f"data:image/png;base64,{b64_data}"


# ==========================================================
# 发送一次 message 风格的 embedding 请求
# ==========================================================
def request_single_embedding(
    content_blocks: List[Dict[str, Any]],
    *,
    model: str = "jinaembeddingv4",
    url: str = "http://localhost:7701/v1/embeddings",
    timeout: float = 30.0,
    max_retries: int = 1,
) -> List[float]:
    """
    对单个 message（content_blocks）发起一次 embedding 请求并返回 embedding 向量。
    content_blocks 示例：
        [{"type": "text", "text": "hello"}]
        [{"type": "text", "text": "hello"}, {"type":"image_url","image_url":{"url": "..."}}
    """
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": content_blocks,
            }
        ],
    }

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            # 打印服务端的错误信息有助于定位问题
            if resp.status_code >= 400:
                try:
                    print(f"[Server Error Body] {resp.text[:500]}")
                except Exception:
                    pass
            resp.raise_for_status()
            data = resp.json()
            # 对应一次请求一个 embedding
            return data["data"][0]["embedding"]
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                print(f"[Warn] request retry {attempt+1}/{max_retries} ...")
            else:
                break

    # 如果重试后仍失败，抛出最后一次的异常
    assert last_err is not None
    raise last_err


# ==========================================================
# 主函数：通过 for 循环逐个请求四种组合
# ==========================================================
def get_multi_embeddings(
    text: str,
    image_path: str,
    *,
    url: str = "http://localhost:7701/v1/embeddings",
    model: str = "jinaembeddingv4",
) -> Dict[str, List[float]]:
    """
    顺序发起四次请求，分别获取：
        1. text
        2. text + text
        3. text + image
        4. image
    """
    image_url = image_to_base64_url(image_path)

    tasks = [
        ("text", [{"type": "text", "text": text}]),
        ("text+text", [{"type": "text", "text": f"{text} {text}"}]),
        ("text+image", [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]),
        ("image", [
            {"type": "image_url", "image_url": {"url": image_url}},
        ]),
    ]

    results: Dict[str, List[float]] = {}
    for name, content_blocks in tasks:
        print(f"==> requesting embedding for: {name}")
        emb = request_single_embedding(
            content_blocks,
            model=model,
            url=url,
            timeout=60.0,      # 适当放宽超时
            max_retries=1,     # 需要可再调大
        )
        results[name] = emb
        print(f"   received dim={len(emb)}")

    return results


# ==========================================================
# 运行示例
# ==========================================================
if __name__ == "__main__":
    text = "Describe the image."
    image_path = "/data2/jproject/OBQA/sample_data/images/cat.png"

    embeddings = get_multi_embeddings(
        text=text,
        image_path=image_path,
        url="http://localhost:7701/v1/embeddings",  # 如有代理/网关请替换
        model="jinaembeddingv4",
    )

    # 打印部分结果
    for name, emb in embeddings.items():
        print(f"\n{name} embedding (first 8 dims): {emb[:8]}")
