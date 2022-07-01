import json
import os
import base64
import pdfkit
import boto3
import dotenv
from urllib.parse import urlparse

INVENTORY_REPORT_NAME = 'Registro de Inventário'
bucket_s3 = 'compufour'
PDF_PATH = '/tmp/out.pdf'
homolog_path = 'homolog/uploads/reports/report/'
production_path = 'production/uploads/reports/report/'
PDFKIT_OPTIONS = {'zoom': 1.3}

dotenv.load_dotenv()

if os.environ['ENVIRONMENT'] in ['production', 'homolog']:
    PATH_WKHTMLTOPDF = '/opt/bin/wkhtmltopdf'
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=PATH_WKHTMLTOPDF)
else:
    PDFKIT_CONFIG = pdfkit.configuration()


def lambda_info(e):
    print('> ', e)


def lambda_error(e):
    print('> ERROR: ', e)


def upload_file(pdf_path: str):
    '''Faz upload para S3'''
    s3_client = boto3.resource('s3')
    file_name = os.path.basename(pdf_path)
    reports_path = production_path if os.environ[
        'ENVIRONMENT'] == 'production' else homolog_path
    bucket_path = reports_path + file_name
    pdf_url = 'https://compufour.s3.amazonaws.com/' + bucket_path

    try:
        lambda_info('Enviando PDF para S3')
        s3_client.meta.client.upload_file(
            pdf_path, bucket_s3, bucket_path, ExtraArgs={'ACL': 'public-read'})
        lambda_info('PDF enviado!')
        lambda_info(pdf_url)
        return pdf_url
    except Exception as e:
        lambda_error(e)


def format_response(response) -> dict:
    '''Formata a resposta HTTP'''
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/pdf",
            "Access-Control-Allow-Origin": "*"
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
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "pdfUrl": response
        })
    }


def format_error_response(e: Exception) -> str:
    return {
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            'environment': os.environ['ENVIRONMENT'],
            'error': str(e),
            'path': os.environ["PATH"]
        })
    }


def convert_from_url(page: str) -> str:
    '''Converte a página para PDF'''
    lambda_info('Iniciando conversão...')

    parsed_url = urlparse(page)
    file_name = os.path.basename(parsed_url.path)
    formatted_file_name = file_name.split(".", 1)[0]
    pdf_path = '/tmp/' + formatted_file_name + ".pdf"
    pdfkit.from_url(page, pdf_path, configuration=PDFKIT_CONFIG)
    return pdf_path


def convert(page: str) -> str:
    '''Converte a página para PDF'''
    pdfkit.from_url(page, PDF_PATH, options=PDFKIT_OPTIONS, configuration=PDFKIT_CONFIG)
    text = open(PDF_PATH, 'rb').read()
    return base64.b64encode(text).decode('utf-8')


def get(event, _) -> dict:
    '''Trabalha a requisição para converter e responder com HTTP'''
    try:
        if event["queryStringParameters"] and event["queryStringParameters"]["reportUrl"]:
            page: str = event["queryStringParameters"]["reportUrl"]
            report_title = event["queryStringParameters"]["reportTitle"]
        else:
            page: str = "www.google.com"
            report_title = ''

        if report_title.replace("+", " ") == INVENTORY_REPORT_NAME:
            pdf_path = convert_from_url(page)
            pdf_uploaded_path = upload_file(pdf_path)
            return format_response_url(pdf_uploaded_path)

        converted: str = convert(page)
        return format_response(converted)
    except Exception as e:
        format_error_response(e)
