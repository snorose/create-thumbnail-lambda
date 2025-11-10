FROM public.ecr.aws/lambda/python:3.11

RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    -o ffmpeg.tar.xz \
    && tar -xJf ffmpeg.tar.xz \
    && mv ffmpeg-*-static/ffmpeg /usr/local/bin/ffmpeg \
    && mv ffmpeg-*-static/ffprobe /usr/local/bin/ffprobe \
    && rm -rf ffmpeg*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]