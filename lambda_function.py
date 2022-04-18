import boto3
import json
import re
import urllib.parse
from pprint import pp
from botocore.errorfactory import ClientError

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

head = """
<!DOCTYPE html>
<html lang="en">
<meta charset="UTF-8">
<title>Quilt Maven</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://maven.quiltmc.org/templates/style.css">
<style>
</style>
<script src=""></script>
<body>
"""

tail = """
</body>
</html>
"""

def index(bucket, folder):
    print('Indexing', folder)
    
    links = ['<a href="..">../</a>']
    
    result = s3_client.list_objects(Bucket='maven.quiltmc.org', Prefix=folder.replace('+', ' '), Delimiter='/')
    
    if (result.get('CommonPrefixes') is not None):
        for obj in result.get('CommonPrefixes'):
            f = obj.get('Prefix')[len(folder):].replace(' ', '+')
            
            if f.endswith('.jar/') or f.endswith('.zip/'):
                continue
            
            l = f'<a href="{f}">{f}</a>'
            
            links.append(f'<p>{l}</p>')

    for obj in bucket.objects.filter(Prefix=folder.replace('+', ' '), Delimiter='/'):
        metadata = s3_client.head_object(Bucket=bucket.name, Key=obj.key)
        
        if 'Metadata' in metadata and 'generated' in metadata['Metadata']:
            continue
        
        file = obj.key[len(folder):].replace(' ', '+')
        
        if file == 'index.html':
            continue
        
        link = f'<a href="{file}">{file}</a>'
        
        if file.endswith('.jar') or file.endswith('.zip'):
            link += f'<a href="{file}/">🗁</a>'
        
        links.append(f'<p>{link}</p>')

    folder = folder.replace(' ', '+')

    if (len(links) == 1):
        return head + f'<h1>{folder}</h1>\n<p>Files not found</p>' + tail
    else:
        return head + f'<h1>{folder}</h1>\n' + '\n'.join(links) + tail
    
def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    bucket = s3_resource.Bucket('maven.quiltmc.org')
    folder = request['uri'][1:]
    
    try:
        result = s3_client.get_object(Bucket=bucket.name, Key=folder.replace('+', ' ') + 'index.html')
        
        result = result['Body'].read().decode('utf-8')
    except ClientError:
        result = index(bucket, folder)
    
    print(result)
    
    return {
        'status': 200,
        'statusDescription': 'OK',
        'headers': {
            'cache-control': [
                {
                    'key': 'Cache-Control',
                    'value': 'max-age=100'
                }
            ],
            'content-type': [
                {
                    'key': 'Content-Type',
                    'value': 'text/html'
                }
            ]
        },
        'body': result
    }
