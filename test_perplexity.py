import requests
import json

url = "http://localhost:5000/api/stream-text"
params = {"topic": "Photosynthesis", "depth": "brief"}

print(f"Connecting to {url}...")
try:
    with requests.get(url, params=params, stream=True, timeout=30) as response:
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            print(f"RX: {json.dumps(data)}") # Print full JSON
                            if "done" in data:
                                print("Stream DONE signal received.")
                        except:
                            print(f"RX Unparsed: {decoded_line}")
        else:
            print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
