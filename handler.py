import json
import os
import base64
import pdfkit
import boto3
from urllib.parse import urlparse

INVENTORY_REPORT_NAME = 'Registro de Inventário'
bucket_s3 = 'compufour'
PDF_PATH = '/tmp/out.pdf'

lambda_task_root_env = os.environ.get("LAMBDA_TASK_ROOT")
lambda_task_root = "" if not lambda_task_root_env else lambda_task_root_env
os.environ["PATH"] = os.environ["PATH"] + ":" + lambda_task_root + "/bin"

def lambda_log(info):
    print('### Log: ', info)

def upload_file(pdf_path: str):
    s3_client = boto3.resource('s3')
    file_name = os.path.basename(pdf_path)
    bucket_path = 'homolog/uploads/reports/report/{}'.format(file_name)
    pdf_url = 'https://compufour.s3.amazonaws.com/' + bucket_path

    try:
        lambda_log('Enviando PDF para S3')
        s3_client.meta.client.upload_file(pdf_path, bucket_s3, bucket_path, ExtraArgs={'ACL':'public-read'})
        lambda_log('PDF enviado!')
        lambda_log(pdf_url)
    except Exception as e:
        lambda_log(e)
    return pdf_url

def format_response(response) -> dict:
    '''Formata a resposta HTTP'''
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/pdf",
            "Access-Control-Allow-Origin" : "*"
        },
        "body": response,
        "isBase64Encoded": True
    }

def format_response_url(response) -> dict:
    '''Formata a resposta HTTP'''
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin" : "*"
        },
        "body": json.dumps({
            "pdfUrl": response
        })
    }

def convert_and_upload(page: str) -> str:
    '''Converte a página para PDF e faz upload para S3'''
    lambda_log('Iniciando conversão...')

    try:
        parsed_url = urlparse(page)
        file_name = os.path.basename(parsed_url.path);
        formatted_file_name = file_name.split(".", 1)[0]
        pdf_path = '/tmp/' + formatted_file_name + ".pdf"
        pdfkit.from_url(page, pdf_path)
        lambda_log(INVENTORY_REPORT_NAME)
        return upload_file(pdf_path)
    except Exception as e:
        print('### Error: ', e)

def convert(page: str) -> str:
    '''Converte a página para PDF'''
    pdfkit.from_url(page, PDF_PATH)
    text = open(PDF_PATH, 'rb').read()
    return base64.b64encode(text).decode('utf-8')

def get(event, _) -> dict:
    '''Trabalha a requisição para converter e responder com HTTP'''
    if event["queryStringParameters"] and event["queryStringParameters"]["reportUrl"]:
        page: str = event["queryStringParameters"]["reportUrl"]
        report_title = event["queryStringParameters"]["reportTitle"]
    else:
        page: str = "www.google.com"
        report_title = ''

    if report_title.replace("+", " ") == INVENTORY_REPORT_NAME:
        converted: str = convert_and_upload(page)
        return format_response_url(converted)

    converted: str = convert(page)
    return format_response(converted)

