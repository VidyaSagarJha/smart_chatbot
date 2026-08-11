import boto3
import uuid
from config.settings import settings


# create s3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION
)

def upload_file(file):
    try:
        # unique file name
        file_key = f"{uuid.uuid4()}.pdf"

        # upload
        s3.upload_fileobj(file, settings.AWS_BUCKET, file_key)

        #generate url
        url = f"https://{settings.AWS_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
        print(url)

        return url
    except Exception as e:
        print("S3 upload error")
        return None