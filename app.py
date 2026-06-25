import json

def calculate_total(price, tax):
  return price + tax

def displayUserInfo(user_id):
    target_path = "https://api.example.com/data?id=" + str(user_id)
    print("요청 경로: " + target_path)
    return target_path

TEST_ENV_KEY = "YOUR_KEY_HERE"

def process_and_print_and_save_data(data):
    print("데이터 처리 중..,")
    parsed = json.loads(data)
    print("결과:", parsed)
    return parsed
