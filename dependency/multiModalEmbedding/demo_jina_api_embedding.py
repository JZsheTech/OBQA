import requests
import json

api_keys = "sk-q8vO7SvcJGTTDOKK6fDf2fDc4d944781922d7dCa5dBb3d49"

url = 'https://aihubmix.com/v1/embeddings'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_keys}' # Replace it by your AiHubMix Key
}

data = {
    "model": "jina-clip-v2",
    "input": [
        {
            "text": "A beautiful sunset over the beach"
        },
        {
            "image": "https://i.ibb.co/nQNGqL0/beach1.jpg"
        },
        {
            "text" : "A beautiful sunset over the beach",
            "image": "R0lGODlhEAAQAMQAAORHHOVSKudfOulrSOp3WOyDZu6QdvCchPGolfO0o/XBs/fNwfjZ0frl3/zy7////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAkAABAALAAAAAAQABAAAAVVICSOZGlCQAosJ6mu7fiyZeKqNKToQGDsM8hBADgUXoGAiqhSvp5QAnQKGIgUhwFUYLCVDFCrKUE1lBavAViFIDlTImbKC5Gm2hB0SlBCBMQiB0UjIQA7"
        }
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))

print(response.json())