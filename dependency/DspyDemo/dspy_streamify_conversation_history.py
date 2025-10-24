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
    history: dspy.History = dspy.InputField()
    answer: str = dspy.OutputField()

predict = dspy.Predict(QA, structured=False)
stream_predict = streamify(predict)

history = dspy.History(messages=[])

async def main():
    print("🚀 Streaming conversation (type 'finish' to exit)\n")

    while True:
        question = input("You: ")
        if question.lower() == "finish":
            break
        print("🤔 Thinking...\n")

        try:
            async for chunk in stream_predict(question=question, history=history):
                if isinstance(chunk, StreamResponse):
                    print(chunk.chunk, end="", flush=True)
                else:
                    # 支持新版 ModelResponseStream / 旧版 Prediction
                    final_answer = getattr(
                        chunk,
                        "response_text",
                        getattr(chunk, "output", getattr(chunk, "answer", str(chunk)))
                    )
                    print(f"\n\n✅ Final Answer: {final_answer}\n")
                    history.messages.append({"question": question, "answer": final_answer})
        except Exception as e:
            import traceback
            print(f"\n❌ Stream failed: {e}\n")
            print("Full traceback:\n", traceback.format_exc())

    dspy.inspect_history()

if __name__ == "__main__":
    asyncio.run(main())
