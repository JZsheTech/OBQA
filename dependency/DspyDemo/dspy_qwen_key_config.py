import dspy

import os
import json

cur_path = os.getcwd()
model_conf_path = os.path.join(cur_path, "../api_key")

model_config_dict = json.load(open(os.path.join(model_conf_path, "mymodelkey.json")))

used_model = "qwen3-8b" # "qwen3-8b" # "llama3.1"

your_openai_api_key = model_config_dict[used_model]["api_key"]
your_openai_base_url = model_config_dict[used_model]["base_url"]
your_openai_compatible_model = model_config_dict[used_model]["model"]
your_openai_other_kwargs = model_config_dict[used_model].get("other_kwargs", {})

os.environ["OPENAI_API_KEY"] = f"{your_openai_api_key}"
os.environ["OPENAI_API_BASE"] = f"{your_openai_base_url}"

dspy.settings.configure(lm=dspy.LM(your_openai_compatible_model, **your_openai_other_kwargs))
