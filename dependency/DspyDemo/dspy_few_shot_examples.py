import dspy

import os
import json

model_config_dict = json.load(open("dependency/api_key/mymodelkey.json"))

# used_model = "gpt-4.1-mini"
used_model = "qwen3-8b" # "qwen3-8b" # "llama3.1"

your_openai_api_key = model_config_dict[used_model]["api_key"]
your_openai_base_url = model_config_dict[used_model]["base_url"]
your_openai_compatible_model = model_config_dict[used_model]["model"]
your_openai_other_kwargs = model_config_dict[used_model].get("other_kwargs", {})

os.environ["OPENAI_API_KEY"] = f"{your_openai_api_key}"
os.environ["OPENAI_API_BASE"] = f"{your_openai_base_url}"

dspy.settings.configure(lm=dspy.LM(your_openai_compatible_model, **your_openai_other_kwargs))

# dspy.settings.configure(lm=dspy.LM("openai/gpt-4o-mini"))


class QA(dspy.Signature):
    question: str = dspy.InputField()
    history: dspy.History = dspy.InputField()
    answer: str = dspy.OutputField()


predict = dspy.Predict(QA)
history = dspy.History(messages=[])

predict.demos.append(
    dspy.Example(
        question="What is the capital of France?",
        history=dspy.History(
            messages=[{"question": "What is the capital of Germany?", "answer": "The capital of Germany is Berlin."}]
        ),
        answer="The capital of France is Paris.",
    )
)

predict(question="What is the capital of America?", history=dspy.History(messages=[]))
dspy.inspect_history()