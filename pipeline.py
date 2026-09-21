import time
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from sqlalchemy import create_engine

# --- Configuration ---
TECH_TAGS = [
    'dev', 'engineer', 'software', 'backend', 'frontend', 'fullstack',
    'python', 'javascript', 'react', 'java',
    'data', 'data-analyst', 'data-science', 'sql',
    'ai', 'machine-learning', 'devops', 'cloud', 'sysadmin'
]
DB_PATH = 'sqlite:///remote_tech_jobs.db'


def extract_jobs(tags):
    """Extract job listings across specified tech tags via RemoteOK API."""
    print("Starting data extraction from RemoteOK API...")
    raw_jobs = []
    
    for tag in tags:
        url = f'https://remoteok.com/api?tag={tag}'
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
            if isinstance(res, list) and len(res) > 1:
                # remoteOK index 0 is legal/meta info
                raw_jobs.extend(res[1:])
        except Exception as e:
            print(f"Error fetching tag '{tag}': {e}")
        time.sleep(1)  # Respect API rate limits
        
    print(f"Extraction complete. Total records collected before deduplication: {len(raw_jobs)}")
    return raw_jobs


def clean_location(val):
    """Normalize location strings, fix character encodings, and handle aliases."""
    if not isinstance(val, str):
        return 'Worldwide / Anywhere'
    
    # Fix Latin-1 / UTF-8 mojibake encoding issues
    try:
        val = val.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
        
    val = val.strip().rstrip(',').strip()
    
    if val.lower() in ['', 'nan', 'none', 'remote', 'remoto', 'worldwide', 'anywhere']:
        return 'Worldwide / Anywhere'
        
    if val.upper() in ['USA', 'US', 'UNITED STATES']:
        return 'United States'
        
    return val


def transform_jobs(raw_jobs):
    """Clean HTML tags, standardize schemas, and resolve data inconsistencies."""
    print("Transforming and cleaning data...")
    
    # 1. Deduplicate by unique job ID
    unique_jobs = list({job['id']: job for job in raw_jobs if 'id' in job}.values())
    
    # 2. Clean HTML descriptions
    cleaned_jobs = []
    for job in unique_jobs:
        job_data = dict(job)
        if 'description' in job_data and job_data['description']:
            soup = BeautifulSoup(job_data['description'], 'html.parser')
            job_data['description'] = soup.get_text(separator=' ', strip=True)
        cleaned_jobs.append(job_data)
        
    df = pd.DataFrame(cleaned_jobs)
    
    # 3. Handle schema transformations
    if 'tags' in df.columns:
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) else str(x))
        
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
    if 'location' in df.columns:
        df['location'] = df['location'].apply(clean_location)
        
    if 'salary_min' in df.columns and 'salary_max' in df.columns:
        df[['salary_min', 'salary_max']] = df[['salary_min', 'salary_max']].replace(0, np.nan)
        
    # 4. Retain only analytical target columns
    target_cols = [
        'id', 'date', 'company', 'position', 'tags',
        'location', 'salary_min', 'salary_max', 'description', 'apply_url'
    ]
    final_df = df[[col for col in target_cols if col in df.columns]].copy()
    
    print(f"Transformation complete. {len(final_df)} clean rows ready for loading.")
    return final_df


def load_to_sqlite(df, db_connection_str):
    """Load transformed DataFrame into SQLite database."""
    print("Connecting to database and saving records...")
    engine = create_engine(db_connection_str)
    df.to_sql('jobs', con=engine, if_exists='replace', index=False)
    print("Successfully updated 'jobs' table in remote_tech_jobs.db!")


def run_pipeline():
    """Execute complete ETL workflow."""
    raw_data = extract_jobs(TECH_TAGS)
    clean_df = transform_jobs(raw_data)
    load_to_sqlite(clean_df, DB_PATH)


if __name__ == '__main__':
    run_pipeline()
