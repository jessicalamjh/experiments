import os
import os.path as path
import re
import requests
import time
import subprocess

# settings
API_BASE_URL = "https://api.semanticscholar.org/datasets/v1/"
API_KEY = "trSDe103BT2qz44Fw9Jks9mlkKfQkjkR2FKM4vpx"
API_HEADERS = {'x-api-key': API_KEY}
RELEASE = "2025-08-05"
## The commented out fields are not used when building the database, so no need to download them
DATASETS = [
    # 's2orc',
    'abstracts', 
    # 'authors', 
    # 'citations', 
    # 'paper-ids', 
    # 'papers', 
    # 'publication-venues', 
]
SLEEP = 1 # max. 10 queries/s
    
def download_file_with_wget(file_url, filepath):
    command = [
        "wget",
        "-O", filepath,
        "--retry-connrefused",
        "--waitretry=600",
        "--read-timeout=20",
        "--timeout=15",
        "-t", "0",
        file_url
    ]
    res = subprocess.run(command)
    return res

def get_latest_release_version( api_base_url ):
    request_url = path.join(api_base_url, "release")
    response = requests.get(request_url, headers=API_HEADERS).json()
    ## this is necessary to avoid frequently querying API
    time.sleep(10)
    return response[-1]

def get_file_urls( api_base_url, release_name, dataset ):
    request_url = path.join(api_base_url, "release", release_name, "dataset", dataset)
    response = requests.get(request_url, headers=API_HEADERS).json()
    file_urls = sorted(response['files'])
    time.sleep(10)
    return file_urls
    
def download_dataset(DATA_DIR):
    ## get the exact latest release name
    try:
        release_name = RELEASE
        assert isinstance(release_name, str)
    except:
        release_name = get_latest_release_version( API_BASE_URL )
    
    for dataset in DATASETS:
        dataset_dir = path.join(DATA_DIR, dataset)
        os.makedirs(dataset_dir, exist_ok=True)
        print(f"Downloading to {dataset_dir}...")

        num_files = len( get_file_urls( API_BASE_URL, release_name, dataset )  )            
        for count in range( num_files ):
            
            num_attemps = 0
            downloading_successful = False
            while num_attemps < 10:
                try:
                    ## get the file_urls every download, because the url has a limited valid time, so we may not
                    ## have enough time to download all 200 s2orc files with one version of file_urls
                    file_url = get_file_urls( API_BASE_URL, release_name, dataset )[count]
                    filename = re.search(f"(?<={dataset}/).*?(?=\?AWS)", file_url).group()
                    filepath = path.join(dataset_dir, filename)
                
                
                    # res_download = requests.get(file_url, allow_redirects=True)
                    # assert res_download.status_code == 200, "Downloading file error. Retry downloading ..."
                    # with open(filepath, 'wb') as f:
                    #     f.write(res_download.content)

                    # wget seems to be slow ...
                    res_download = download_file_with_wget(file_url, filepath)
                    assert res_download.returncode == 0, "Downloading file error. Retry downloading ..."

                    assert filepath.endswith(".gz")
                    print("unzipping ...")
                    
                    res = subprocess.run( ["gunzip", filepath] )
                    assert res.returncode == 0, "Unzipping error. Retry downloading ..."

                    ## remove the .gz file if exists.
                    if filepath.endswith(".gz") and os.path.exists( filepath ):
                        os.remove( filepath )
                    
                    print(f"- done with {filepath}")
                    downloading_successful = True
                    break
                except:
                    num_attemps += 1
                    print(f"- something went wrong with {filepath}. Retrying downloading ({num_attemps})")
                    ## idle for 10 min
                    time.sleep(600)

            assert downloading_successful, f"Error: downloading {filepath} failed! Quit."

            time.sleep(10)
        time.sleep(SLEEP)
    print("Downloading finished!")


if __name__=="__main__":
    download_dataset("data/raw")