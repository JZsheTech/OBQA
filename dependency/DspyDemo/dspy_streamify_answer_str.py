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
    output_stream = stream_predict(question="How to use the DsPY automatic prompt tuning framework?")

    async for chunk in output_stream:      
        return_value = None  
        if isinstance(chunk, dspy.streaming.StreamResponse):
            print(f"Output token of field {chunk.signature_field_name}: {chunk.chunk}")
        elif isinstance(chunk, dspy.Prediction):
            return_value = chunk
            
    return return_value


program_output = asyncio.run(read_output_stream())
print("Final output: ", program_output)