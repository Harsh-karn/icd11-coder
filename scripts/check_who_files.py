import urllib.request

patterns = [
    'Index-ICD-11-MMS-en.zip',
    'Linearization-ICD-11-MMS-en.zip',
    'LinearizationPrint-ICD-11-MMS-en.zip',
    'Foundation-ICD-11-en.zip',
    'ICD-11-MMS-en.zip',
    'ClaML-ICD-11-MMS-en.zip',
    'Tabulation-ICD-11-MMS-en.zip',
    'VersionDetails.txt',
    'readme.txt',
    'SimpleTabulation-ICD-11-MMS-en.zip'
]

for p in patterns:
    url = f'https://icdcdn.who.int/static/releasefiles/2026-01/{p}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        cl = res.headers.get('Content-Length')
        print(f'{p}: FOUND (status {res.status}, len {cl})')
    except Exception as e:
        print(f'{p}: not found')
