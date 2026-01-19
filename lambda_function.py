import boto3
import os
import json
from PIL import Image, ImageOps
import subprocess

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
thumbnail_bucket = 'snorose-public-bucket'
sqs_queue_url = os.environ.get('SQS_QUEUE_URL')

IMG_EXT_LIST = ["jpg","jpeg","png","jfif","bmp","webp"]
VDO_EXT_LIST = ["mp4","mov"]

FFMPEG_BIN = "/opt/bin/ffmpeg"

def create_video_thumbnail_image(download_path, resized_path, quality=70):
    """
    비디오에서 첫 번째 프레임을 추출하여 썸네일 생성
    예외 발생 시 상위 함수에서 처리
    """
    cmd = [
        FFMPEG_BIN,
        "-i", download_path,
        "-vframes", "1",
        "-q:v", str(quality),
        resized_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    create_thumbnail_image(resized_path, resized_path)

def create_thumbnail_image(image_path, resized_path, size=256, quality=30):
    """
    썸네일용 이미지 리사이징 (비율 유지, 짧은 변 최대 길이 thumb_size 제한, 256 * 256 크기로 crop), WebP 포맷
    """
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)

        # 긴 변 기준 리사이즈 (비율 유지)
        width, height = image.size
        scale = size / min(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = image.resize((new_width, new_height), Image.LANCZOS)

        # 중앙 기준 crop
        left = (new_width - size) // 2
        top = (new_height - size) // 2
        right = left + size
        bottom = top + size
        image = image.crop((left, top, right, bottom))

        # WebP 포맷으로 저장 (품질 30%, 최적화 옵션 적용)
        image.save(resized_path, format='WEBP', quality=quality, optimize=True)

def delete_existing_thumbnails(bucket, prefix):
    """prefix 경로에 있는 모든 객체 삭제"""
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

    if 'Contents' in response:
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        if objects_to_delete:
            s3_client.delete_objects(
                Bucket=bucket, 
                Delete={'Objects': objects_to_delete}
            )

def send_optimization_complete_message(s3_file_name, success, error_message=None):
    """
    썸네일 최적화 완료 메시지를 SQS로 전송
    """
    if not sqs_queue_url:
        print("SQS_QUEUE_URL 환경변수가 설정되지 않았습니다.")
        return
    
    message = {
        "s3FileName": s3_file_name,
        "success": success
    }
    
    if error_message:
        message["errorMessage"] = error_message
    
    try:
        sqs_client.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=json.dumps(message)
        )
        print(f"[SQS] Sent optimization complete message: {message}")
    except Exception as e:
        print(f"[SQS ERROR] Failed to send optimization complete message: {e}")
        # SQS 전송 실패 시 Lambda 실패로 처리하여 재시도 유발 (최대 3회)
        raise RuntimeError(f"SQS message send failed: {e}")

def lambda_handler(event, context):
    """
    event 예시 구조:
    {
        "bucket": "원본 이미지가 저장된 버킷",
        "key": "원본 이미지의 키 (S3 경로)"
    }
    """
    download_path = None
    upload_path = None
    filename = None
    
    try:
        bucket = event['bucket']
        key = event['key']
        post_id = key.split('/')[1]
        if not post_id.isdigit():
            error_msg = f"Post id not in format: {key}"
            print(error_msg)
            return {
                "statusCode": 400,
                "body": error_msg
            }

        filename = os.path.basename(key)
        base_name = filename.rsplit('.', 1)[0]
        ext       = filename.lower().rsplit('.', 1)[-1]
        thumb_filename = f"thumbnail-{base_name}.webp"

        download_path = f'/tmp/{filename}'
        upload_path = f'/tmp/{thumb_filename}'

        # 기존 썸네일 삭제
        thumbnail_prefix = f'post-thumbnail/{post_id}/'
        delete_existing_thumbnails(thumbnail_bucket, thumbnail_prefix)
        print(f"Deleted existing thumbnails under {thumbnail_prefix}")

        if filename == "":
            # 빈 파일명 - 썸네일 삭제 성공 (최적화 작업이 아니므로 SQS 전송 안함)
            return {
                "statusCode": 200,
                "body": "Thumbnail deleted successfully."
            }
        else:
            # 원본 이미지 다운로드
            s3_client.download_file(bucket, key, download_path)
            print(f"Downloaded original image {key} from bucket {bucket}")

            # 썸네일 생성
            if ext in IMG_EXT_LIST:
                create_thumbnail_image(download_path, upload_path)
            elif ext in VDO_EXT_LIST:
                create_video_thumbnail_image(download_path, upload_path)
            else:
                error_msg = f"Attachment extension {ext} unsupported: {filename}"
                send_optimization_complete_message(
                    s3_file_name=filename,
                    success=False,
                    error_message=error_msg
                )
                return {
                    "statusCode": 400,
                    "body": error_msg
                }
            print(f"Thumbnail created at {upload_path}")

            # 썸네일 업로드
            thumb_key = f'post-thumbnail/{post_id}/{thumb_filename}'
            with open(upload_path, 'rb') as f:
                s3_client.upload_fileobj(
                    f,
                    thumbnail_bucket,
                    thumb_key,
                    ExtraArgs={
                        'ContentType': 'image/webp',
                        'ACL': 'public-read',
                        'CacheControl': 'public, max-age=31536000'
                    }
                )
            print(f"Uploaded thumbnail to {thumbnail_bucket}/{thumb_key}")
            
            # 성공 메시지 전송
            send_optimization_complete_message(
                s3_file_name=filename,
                success=True
            )

            return {
                "statusCode": 200,
                "body": f"Thumbnail created successfully: {thumb_key}"
            }

    except Exception as e:
        print(f"Error processing {key}: {e}")
        
        # 실패 메시지 전송
        if filename:  # 파일명이 있는 경우에만 전송
            send_optimization_complete_message(
                s3_file_name=filename,
                success=False,
                error_message=str(e)
            )
        
        return {
            "statusCode": 500,
            "body": f"Failed to create thumbnail: {str(e)}"
        }
    finally:
        for path in [download_path, upload_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except:
                # 파일 삭제 오류 무시
                pass
        
