# scraping_and_parsing

## List of contents

 - scripts
    - get_papers_by_doi.py - Download open access journals accessible through PubMed Central by their DOIs.

## Setup

This repo uses [uv](https://docs.astral.sh/uv/) for environment management.

```
uv sync
uv run scripts/get_papers_by_doi.py <doi>
```

Optionally set an NCBI API key via the `NCBI_API_KEY` environment variable to raise rate limits, or pass `--api_key`.
