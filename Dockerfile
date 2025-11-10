# 1. AWS 공식 Python 3.11 람다 이미지를 기반으로 사용
FROM public.ecr.aws/lambda/python:3.11

# 2. yum을 사용해 ffmpeg 바이너리를 설치
RUN yum install -y ffmpeg

# 3. requirements.txt 파일을 이미지 안으로 복사
COPY requirements.txt .

# 4. pip를 사용해 Python 라이브러리 (Pillow, boto3) 설치
RUN pip install -r requirements.txt

# 5. 사용자의 람다 코드를 이미지의 작업 디렉터리로 복사
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# 6. 람다 함수가 호출될 때 실행할 핸들러를 지정
CMD [ "lambda_function.lambda_handler" ]