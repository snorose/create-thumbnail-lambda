FROM public.ecr.aws/lambda/python:3.11

RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y ffmpeg && \
    yum clean all

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]