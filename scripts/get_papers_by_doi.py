### MININAL PYTHON VERSION REQUIRED IS 3.10 !!!
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
#     "tqdm",
# ]
# ///
import requests
import re
import os
import time
import argparse
import logging
from tqdm import tqdm
from typing import Callable, List
logging.basicConfig(
    filename='get_by_doi.log', 
    filemode='w',
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    )

def add_api_key(api_key: str | None) -> Callable[[str], str]:
    def attach_api_key(url: str) -> str:
        if api_key:
            return url+f'&api_key={api_key}'
        return url
    return attach_api_key

def download_via_ftp(href_url: str) -> None:
    # NCBI moved the OA bulk files under /pub/pmc/deprecated/ and dropped FTP
    # access in favor of HTTPS, but oa.fcgi still returns the old ftp:// path.
    download_url = href_url.replace(
        'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/',
        'https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/',
        )

    _, local_file_path = os.path.split(download_url)

    response = requests.get(download_url, stream=True)
    if response.status_code != 200:
        logging.error(f"Failed to download {download_url}: HTTP {response.status_code}")
        return

    with open(local_file_path, 'wb') as local_file:
        for chunk in response.iter_content(chunk_size=8192):
            local_file.write(chunk)

    logging.info(f"File downloaded successfully to {local_file_path}")

def get_publication_by_pmc_id(pmc_id: str, api_key: str = None) -> None:
    url = f'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmc_id}'
    url = add_api_key(api_key)(url)
    # print(url)
    response = requests.get(url)
    if response.status_code == 200:
        # Extract the FTP address of the demanded file
        content = response.content.decode("utf-8")
        href_regexp = 'href=".*"'
        href_url_tagged, *_ = re.findall(href_regexp, content)
        href_url = href_url_tagged.replace('href="', '').replace('"', '')
        # Download file
        download_via_ftp(href_url)
    else:
        logging.error(f"{pmc_id}: Error fetching article metadata")

def doi_to_pmc_id(doi: str, api_key: str | None = None) -> str | None:
    # The base URL for E-utilities
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # Prepare the Esearch URL to search for the DOI in PubMed
    esearch_url = f"{base_url}esearch.fcgi?db=pubmed&term={doi}[doi]&retmode=json"
    
    esearch_url = add_api_key(api_key)(esearch_url)
    
    response = requests.get(esearch_url)
    data = response.json()
    
    # Extract PMID from the response
    pmid_list = data['esearchresult']['idlist']
    if pmid_list:
        pmid = pmid_list[0]
        logging.info(f"PMID: {pmid}")
    else:
        logging.info("DOI not found in PubMed")
        pmid = None
    
    if pmid:
        # Prepare the ELink URL to link from PubMed to PMC
        elink_url = f"{base_url}elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"
        elink_url = add_api_key(api_key)(elink_url)
        
        response = requests.get(elink_url)
        link_data = response.json()
        
        # Attempt to extract PMC ID from the response
        try:
            pmc_id = link_data['linksets'][0]['linksetdbs'][0]['links'][0]
            return pmc_id
        except (IndexError, KeyError):
            logging.error(f"PMC ID not found for the given DOI: {doi}")
    return None

def get_paper_by_doi(doi: str, api_key: str | None = None) -> None:
    logging.info(f"Looking for DOI: {doi}")
    pmc_id_num = doi_to_pmc_id(doi, api_key)
    if pmc_id_num:
        pmc_id = "PMC"+pmc_id_num
        get_publication_by_pmc_id(
            pmc_id=pmc_id,
            api_key=api_key
            )
        
def get_papers(dois: List[str], api_key: str | None = None, wait: float = 0.33) -> None:
    t0 = time.time()
    for doi in tqdm(dois):
        get_paper_by_doi(doi, api_key)
        # Wait for a while to avoid being blocked by the server 
        # Default minimal interval between requests is 0.33s
        while ((time.time()-t0) < wait):
            time.sleep(0.1*wait)
        t0 = time.time()

def read_file(fname: str) -> List[str]:
    return list(filter(None, [item.strip() if item else None for item in open(fname, "r").readlines()]))

def main() -> None:
    parser = argparse.ArgumentParser(description="Download papers from PubMed Central by DOI")
    parser.add_argument("doi", type=str, help="DOIs to download or file with DOIs line by line")
    parser.add_argument("--api_key", type=str, default=os.environ.get("NCBI_API_KEY"), help="NCBI API key (defaults to NCBI_API_KEY env var)")
    parser.add_argument("--wait", type=float, default=0.33, help="Time to wait between requests")
    args = parser.parse_args()

    if os.path.isfile(args.doi):
        dois = read_file(args.doi)
    else:
        dois = [args.doi]

    get_papers(dois, args.api_key, args.wait)

if __name__ == "__main__":
    main()