import requests

def http_get(url: str):
    return requests.get(url).json()

def http_post(url: str, payload: dict):
    return requests.post(url, json=payload).json()
