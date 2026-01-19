FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y tar xz curl && yum clean all

RUN mkdir -p /opt/bin && \
    curl -L https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz \
    -o ffmpeg.tar.xz && \
    tar -xJf ffmpeg.tar.xz && \
    cp ffmpeg-*/bin/ffmpeg /opt/bin/ && \
    cp ffmpeg-*/bin/ffprobe /opt/bin/ && \
    chmod +x /opt/bin/ffmpeg /opt/bin/ffprobe && \
    rm -rf ffmpeg*

ENV PATH="/opt/bin:${PATH}"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]