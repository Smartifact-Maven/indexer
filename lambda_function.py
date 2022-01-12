import json
import re
import urllib.parse
from pprint import pp

import boto3

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

def index_version(bucket, artifact, directory, version, links, resources):
    url_version = version.replace('+', ' ')
    version_prefix = f'{directory}/{url_version}/'

    pom = f'{version_prefix}{artifact}-{url_version}.pom'

    summary = s3_resource.ObjectSummary(bucket, pom)
    modified = summary.last_modified.timestamp()

    head = s3_client.head_object(Bucket=bucket, Key=pom)

    uploader = head['Metadata']['uploader']

    version_resources = ""

    for object in s3_resource.Bucket(bucket).objects.filter(Prefix=version_prefix):
        url_text = object.key[(object.key.rindex('/') + 1):]
        text = url_text.replace(' ', '+')
        head = s3_client.head_object(Bucket=bucket, Key=object.key)
        size = head['ContentLength']

        version_resources += f'<tr><td class="resource" onclick="event.stopPropogation();"><a href="./{url_version}/{url_text}">{text}</a></td></p><td><p>{size}</p></td></tr>'

    files = f'<table class=\\"files\\"><thead><th>File</th><th>Size (bytes)</th></thead><tbody>{version_resources}</tbody></table>'

    entries = [
        f'<td><details><summary>{version}</summary>{files}</details></td>',
        f'<td><p class="time">{modified}</p></td>',
        f'<td><p>{uploader}</p></td>\n    '
    ]

    links.append('<tr class="version" id="{}">\n      {}</tr>'.format(version, '\n      '.join(entries)))


def directories(bucket, directory, style):
    dirs = directory.split('/')
    results = []
    length = len(dirs) - 1
    folder = ''
    
    results.append('<a href="' + ('../' * len(dirs)) + '">repositories</a>')
    
    page_template = s3_resource.Object(bucket, 'templates/directory_template.html').get()['Body'].read().decode('utf-8')

    for i in range(length):
        d = dirs[i]
        h = ('../' * (length - i))

        results.append(f'<a href={h}index.html>{d}</a>')
        
        folder += d + '/'
        
        folders = set()
        
        folders.add('..')
        
        for object in s3_resource.Bucket(bucket).objects.filter(Prefix=folder):
            cut = object.key[len(folder):]
            
            if ('/' in cut):
                folders.add(cut[:cut.index('/')])
        
        if len(folders) > 0:
            folders = list(map(lambda x: f'<li><a href="./{x}">{x}</a></li>', folders))
            folders.sort()
            
            folders = '\n'.join(folders)
                
            page = page_template.replace('${DIRECTORY}', folder) \
                .replace('${DIRECTORIES}', folders) \
                .replace('${STYLE}', style)
            
            object = s3_resource.Object(bucket, f'{folder}index.html')
            object.put(Body = page, ContentType='text/html')
            
    folders = set()
        
    for object in s3_resource.Bucket(bucket).objects.all():
        key = object.key
        
        if ('/' in key):
            key = key[:key.index('/')]
            
            if key != 'templates':
                folders.add(key)
    
    if len(folders) > 0:
        folders = list(map(lambda x: f'<li><a href="./{x}">{x}</a></li>', folders))
        folders.sort()
        
        folders = '\n'.join(folders)
            
    root = page_template.replace('${DIRECTORY}', 'Repositories') \
        .replace('${DIRECTORIES}', folders) \
        .replace('${STYLE}', style)
    
    object = s3_resource.Object(bucket, 'index.html')
    object.put(Body = root, ContentType='text/html')

    return '/'.join(results) + '/' + dirs[-1]

def generate_parent_indices(directory):
    parent = directory[0:directory.rfind('/')]


def lambda_handler(event, context):
    metadata = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    match = re.search(r'.*/(.*)/.*$', metadata)

    artifact = match.group(1)

    directory = metadata[0:metadata.rfind('/')]

    bucket = event['Records'][0]['s3']['bucket']['name']

    metadata = s3_resource.Object(bucket, metadata).get()['Body'].read().decode('utf-8')

    versions = re.findall(r'<version>(.*)</version>', metadata)

    versions.sort(key=lambda x: [int(y.split('-', 1)[0].split('+', 1)[0]) for y in x.split('.')])

    links = []
    resources = []

    for version in versions:
        index_version(bucket, artifact, directory, version, links, resources)
        
    style = s3_resource.Object(bucket, 'templates/style.css').get()['Body'].read().decode('utf-8')

    index = s3_resource.Object(bucket, 'templates/artifact_template.html').get()['Body'].read().decode('utf-8') \
        .replace('${ARTIFACT_ID}', artifact) \
        .replace('${CURRENT_DIRECTORY}', directories(bucket, directory, style)) \
        .replace('${VERSION_LIST}', '\n    '.join(links)) \
        .replace('${VERSION_RESOURCES}', '[\n    {}\n  ]'.format(',\n    '.join(resources))) \
        .replace('${STYLE}', style)
        
    generate_parent_indices(directory)

    object = s3_resource.Object(bucket, f'{directory}/index.html')
    object.put(Body = index, ContentType='text/html')

    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Static pages generated')
    }
