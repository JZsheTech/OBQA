from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
#   extra_headers={
#     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
#     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
#   },
  extra_body={},
  model="x-ai/grok-4.1-fast",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)

print(completion.choices[0].message.content)

# # First API call with reasoning
# response = client.chat.completions.create(
#   model="x-ai/grok-4.1-fast",
#   messages=[
#           {
#             "role": "user",
#             "content": "How many r's are in the word 'strawberry'?"
#           }
#         ],
#   extra_body={"reasoning": {"enabled": True}}
# )

# # Extract the assistant message with reasoning_details
# response = response.choices[0].message
# print("First response:", response.content)

# # Preserve the assistant message with reasoning_details
# messages = [
#   {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
#   {
#     "role": "assistant",
#     "content": response.content,
#     "reasoning_details": response.reasoning_details  # Pass back unmodified
#   },
#   {"role": "user", "content": "Are you sure? Think carefully."}
# ]

# # Second API call - model continues reasoning from where it left off
# response2 = client.chat.completions.create(
#   model="x-ai/grok-4.1-fast",
#   messages=messages,
#   extra_body={"reasoning": {"enabled": False}}
# )
# print("Second response:", response2.choices[0].message.content)