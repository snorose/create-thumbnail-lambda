import boto3
import json
import base64
import re
import time
import os

REGION_NAME = os.environ.get('REGION_NAME')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
IMAGE_KEY = "test/12345/test_video.mp4"
LAMBDA_FUNCTION_NAME = os.environ.get('LAMBDA_FUNCTION_NAME')
ECR_REPOSITORY_NAME = os.environ.get('ECR_REPOSITORY_NAME')

client = boto3.client('lambda', region_name=REGION_NAME)

# 이벤트 객체
payload_data = {
    "bucket": BUCKET_NAME,
    "key": IMAGE_KEY
}
payload_bytes = json.dumps(payload_data).encode('utf-8')

def trigger_cold_start(func_name):
    """
    함수의 환경 변수에 현재 시간을 업데이트하여 강제로 Cold Start 환경을 조성함
    """
    print(f"[Setup] {func_name} 환경 변수 업데이트 중 (Cold Start 유도)...")
    
    config = client.get_function_configuration(FunctionName=func_name)
    env_vars = config.get('Environment', {}).get('Variables', {})
    
    # 임의의 변수 업데이트
    env_vars['TEST_TIMESTAMP'] = str(time.time())
    
    client.update_function_configuration(
        FunctionName=func_name,
        Environment={'Variables': env_vars}
    )
    
    print(f"{func_name} 업데이트 진행 중...")
    while True:
        response = client.get_function(FunctionName=func_name)
        status = response['Configuration']['LastUpdateStatus']
        state = response['Configuration']['State']
        
        if state == 'Active' and status == 'Successful':
            print("업데이트 완료! \n")
            break
        elif status == 'Failed':
            raise Exception(f"함수 업데이트 실패: {response['Configuration']['LastUpdateStatusReason']}")
            
        time.sleep(2)

def run_test(func_name, label):
    # 테스트 직전, 강제로 Cold Start 유발
    trigger_cold_start(func_name)
    
    print(f"▶ Testing: {label} [{func_name}]")
    
    try:
        start_time = time.time()
        response = client.invoke(
            FunctionName=func_name,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=payload_bytes
        )
        end_time = time.time()

        log_result = base64.b64decode(response['LogResult']).decode('utf-8')
        
        # Init Duration 추출
        init_match = re.search(r"Init Duration:\s*([\d.]+)\s*ms", log_result)
        duration_match = re.search(r"Duration:\s*([\d.]+)\s*ms", log_result)
        
        init_time = float(init_match.group(1)) if init_match else 0.0
        exec_time = float(duration_match.group(1)) if duration_match else 0.0

        print(f"   ▷ [Total Client Latency] : {round((end_time - start_time) * 1000, 2)} ms")
        print(f"   ▷ [Lambda Execution]     : {exec_time} ms")
        
        # Cold Start 결과 강조
        if init_time > 0:
            print(f"   [Cold Start Init]      : {init_time} ms")
        else:
            print(f"   [Cold Start Init]      : 0 ms (실패: 이미 Warm 상태임)")

    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    print("=== Lambda 성능 비교 테스트 시작 ===\n")
    
    # Console 버전 테스트
    run_test(LAMBDA_FUNCTION_NAME, "Console Version")
    
    # Container 버전 테스트
    run_test(ECR_REPOSITORY_NAME, "Container Image Version")
    
    print("\n=== 테스트 완료 ===")