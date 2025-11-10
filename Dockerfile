FROM public.ecr.aws/lambda/python:3.11

RUN curl -L https://raw.githubusercontent.com/eugeneware/ffmpeg-static/master/bin/linux/x64/ffmpeg \
    -o /usr/local/bin/ffmpeg \
    && chmod +x /usr/local/bin/ffmpeg

RUN curl -L https://raw.githubusercontent.com/eugeneware/ffmpeg-static/master/bin/linux/x64/ffprobe \
    -o /usr/local/bin/ffprobe \
    && chmod +x /usr/local/bin/ffprobe

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]