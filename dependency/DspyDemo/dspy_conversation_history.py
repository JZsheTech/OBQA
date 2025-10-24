import dspy
import os
import json

model_config_dict = json.load(open("dependency/api_key/mymodelkey.json"))

# used_model = "gpt-4.1-mini"
used_model = "qwen3-8b" # "llama3.1"

your_openai_api_key = model_config_dict[used_model]["api_key"]
your_openai_base_url = model_config_dict[used_model]["base_url"]
your_openai_compatible_model = model_config_dict[used_model]["model"]
your_openai_other_kwargs = model_config_dict[used_model].get("other_kwargs", {})

os.environ["OPENAI_API_KEY"] = f"{your_openai_api_key}"
os.environ["OPENAI_API_BASE"] = f"{your_openai_base_url}"

dspy.settings.configure(lm=dspy.LM(your_openai_compatible_model, **your_openai_other_kwargs))

class QA(dspy.Signature):
    question: str = dspy.InputField()
    history: dspy.History = dspy.InputField()
    answer: str = dspy.OutputField()

# predict = dspy.Predict(QA)
predict = dspy.Predict(QA, structured=False)

history = dspy.History(messages=[])

while True:
    question = input("Type your question, end conversation by typing 'finish': ")
    if question == "finish":
        break
    outputs = predict(question=question, history=history) # 多轮对话中之后的question有可能基于前面的QA对被LLM改写。-llama3.1会这样
    print(f"\n{outputs.answer}\n")
    history.messages.append({"question": question, **outputs})

dspy.inspect_history()