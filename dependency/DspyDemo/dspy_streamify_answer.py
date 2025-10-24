import dspy
import os
import json
import asyncio
from dspy.streaming import streamify, StreamResponse

model_config_dict = json.load(open("dependency/api_key/mymodelkey.json"))
used_model = "qwen3-8b-thinking"
conf = model_config_dict[used_model]

# ⚠️ 确保 JSON 里不要再有 "stream": true
lm_kwargs = conf.get("other_kwargs", {}).copy()
lm_kwargs.pop("stream", None)

os.environ["OPENAI_API_KEY"] = conf["api_key"]
os.environ["OPENAI_API_BASE"] = conf["base_url"]

dspy.settings.configure(lm=dspy.LM(conf["model"], **lm_kwargs))

class QA(dspy.Signature):
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

predict = dspy.Predict(QA, structured=False)


# Enable streaming for the 'answer' field
stream_predict = dspy.streamify(
    predict,
    stream_listeners=[dspy.streaming.StreamListener(signature_field_name="answer")],
)
import asyncio

async def read_output_stream():
    output_stream = stream_predict(question="Please explain asynchronous programming in Python in detail.")

    async for chunk in output_stream:
        print(chunk)

asyncio.run(read_output_stream())

"""
打印结果展示:
StreamResponse(predict_name='self', signature_field_name='answer', chunk='Asynchronous programming in Python enables the execution of multiple operations concurrently, improving efficiency for I/O-bound and high-latency tasks.', is_last_chunk=False)

StreamResponse(predict_name='self', signature_field_name='answer', chunk=' It relies on **coroutines**, **event loops**, and **non-blocking I', is_last_chunk=False)

StreamResponse(predict_name='self', signature_field_name='answer', chunk="/O** to manage tasks without blocking the main thread. Here's a detailed breakdown", is_last_chunk=False)

Prediction(
    answer='Asynchronous programming in Python enables the execution of multiple operations concurrently, improving efficiency for I/O-bound and high-latency tasks. It relies on **coroutines**, **event loops**, and **non-blocking I/O** to manage tasks without blocking the main thread. Here\'s a detailed breakdown:\n\n### Key Concepts:\n1. **Coroutines**: \n   - Defined using `async def`, coroutines are functions that can suspend their execution and resume later. They run in a cooperative multitasking model.\n   - Example: `async def fetch_data(): ...` defines a coroutine.\n\n2. **Event Loop**:\n   - The core of asynchronous programming, managed by `asyncio`, which schedules and runs coroutines. It handles I/O operations and callbacks.\n   - Example: `asyncio.run(fetch_data())` starts the event loop.\n\n3. **`await` Keyword**:\n   - Pauses a coroutine until another coroutine completes, allowing the event loop to handle other tasks during the wait.\n   - Example: `await asyncio.sleep(1)` pauses execution for 1 second without blocking the thread.\n\n4. **Non-Blocking I/O**:\n   - Asynchronous code avoids blocking by offloading I/O operations (e.g., network requests, file reads) to background threads or asynchronous libraries (e.g., `aiohttp`, `aiomysql`).\n\n### Use Cases:\n- **I/O-bound Tasks**: Ideal for network requests, API calls, or file operations where the program waits for external resources.\n- **High-Concurrency Applications**: Servers handling many simultaneous connections (e.g., chat apps, real-time data streams).\n\n### Example:\n```python\nimport asyncio\n\nasync def count(name, n):\n    for i in range(1, n+1):\n        print(f"{name}: {i}")\n        await asyncio.sleep(0.1)  # Non-blocking sleep\n\nasync def main():\n    await asyncio.gather(count("A", 3), count("B", 5))\n\nasyncio.run(main())\n```\nThis code runs two counters concurrently, printing results interleaved.\n\n### Limitations:\n- **Not for CPU-bound tasks**: Async is less effective for heavy computations, which should use multiprocessing or multithreading.\n- **Complexity**: Requires careful management of state and error handling.\n\n### Libraries:\n- **`asyncio`**: Standard library for asynchronous I/O.\n- **`aiohttp`**: Asynchronous HTTP client/server.\n- **`asyncpg`**: Async PostgreSQL database driver.\n\nIn summary, asynchronous programming in Python leverages coroutines and an event loop to maximize resource utilization, making it ideal for scalable, I/O-heavy applications.'
"""