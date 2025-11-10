FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/bin && \
    curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    -o ffmpeg.tar.xz && \
    tar -xJf ffmpeg.tar.xz && \
    mv ffmpeg-*-static/ffmpeg /opt/bin/ffmpeg && \
    mv ffmpeg-*-static/ffprobe /opt/bin/ffprobe && \
    chmod +x /opt/bin/ffmpeg /opt/bin/ffprobe && \
    rm -rf ffmpeg*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]