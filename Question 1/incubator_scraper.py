"""
========================================================================================
STARTUP INCUBATOR WEB ARCHIVAL & CURRENT SCRAPER
========================================================================================
Author: Research Associate (RA)
Project: Empirical Study of Indian Startup Incubators
Scope:
  Automate collection of:
    (i)  Homepage
    (ii) About Us page
  Across:
    - Current Live Websites
    - Historical Archived Websites (Wayback Machine / Internet Archive)
  Frequency & Range:
    - Earliest available page every month from September 2026 back to January 2022
      (57 months total per target page)
========================================================================================
"""

import os
import sys
import time
import json
import hashlib
import logging
import argparse
from datetime import datetime
from urllib.parse import urlparse
import requests

# --------------------------------------------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraping_execution.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("IncubatorScraper")

# --------------------------------------------------------------------------------------
# TARGET INCUBATOR DIRECTORY & URL MAPPINGS
# --------------------------------------------------------------------------------------
INCUBATORS = [
    {
        "slug": "t_hub",
        "name": "T-Hub (Technology Hub)",
        "home_url": "https://t-hub.co",
        "about_url": "https://t-hub.co/about-us"
    },
    {
        "slug": "iitm_incubation_cell",
        "name": "IIT Madras Incubation Cell (IITMIC)",
        "home_url": "https://incubation.iitm.ac.in",
        "about_url": "https://incubation.iitm.ac.in/about-us"
    },
    {
        "slug": "iima_ventures",
        "name": "IIMA Ventures (formerly CIIE.CO)",
        "home_url": "https://iimaventures.com",
        "about_url": "https://iimaventures.com/about"
    },
    {
        "slug": "nsrcel_iimb",
        "name": "NSRCEL (IIM Bangalore)",
        "home_url": "https://nsrcel.org",
        "about_url": "https://nsrcel.org/about-us"
    },
    {
        "slug": "sine_iit_bombay",
        "name": "SINE (IIT Bombay)",
        "home_url": "https://sineiitb.org",
        "about_url": "https://sineiitb.org/about-us"
    },
    {
        "slug": "venture_center",
        "name": "Venture Center (CSIR-NCL Pune)",
        "home_url": "https://venturecenter.co.in",
        "about_url": "https://venturecenter.co.in/about"
    },
    {
        "slug": "ccamp",
        "name": "C-CAMP (Centre for Cellular & Molecular Platforms)",
        "home_url": "https://ccamp.res.in",
        "about_url": "https://ccamp.res.in/about-us"
    },
    {
        "slug": "fitt_iit_delhi",
        "name": "FITT (IIT Delhi)",
        "home_url": "https://fitt-iitd.in",
        "about_url": "https://fitt-iitd.in/web/about-fitt"
    },
    {
        "slug": "siic_iit_kanpur",
        "name": "SIIC (IIT Kanpur)",
        "home_url": "https://siicincubator.com",
        "about_url": "https://siicincubator.com/about"
    },
    {
        "slug": "kerala_startup_mission",
        "name": "Kerala Startup Mission (KSUM)",
        "home_url": "https://startupmission.kerala.gov.in",
        "about_url": "https://startupmission.kerala.gov.in/about"
    },
    {
        "slug": "bits_pieds",
        "name": "PIEDS (BITS Pilani)",
        "home_url": "https://pieds-bitspilani.org",
        "about_url": "https://pieds-bitspilani.org/about"
    },
    {
        "slug": "axilor_ventures",
        "name": "Axilor Ventures",
        "home_url": "https://axilor.com",
        "about_url": "https://axilor.com/about"
    },
    {
        "slug": "villgro",
        "name": "Villgro Innovations Foundation",
        "home_url": "https://villgro.org",
        "about_url": "https://villgro.org/about-us"
    },
    {
        "slug": "ikp_knowledge_park",
        "name": "IKP Knowledge Park",
        "home_url": "https://ikpknowledgepark.com",
        "about_url": "https://ikpknowledgepark.com/about-us"
    },
    {
        "slug": "kiit_tbi",
        "name": "KIIT-TBI (Odisha)",
        "home_url": "https://kiitincubator.in",
        "about_url": "https://kiitincubator.in/about-us"
    }
]

# --------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------------------
def generate_monthly_timestamps(start_year=2022, start_month=1, end_year=2026, end_month=9):
    """
    Generates a list of (year, month, YYYYMM, target_date_str) from January 2022 to September 2026.
    Total: 57 calendar months.
    """
    monthly_intervals = []
    current_y = start_year
    current_m = start_month
    
    while (current_y < end_year) or (current_y == end_year and current_m <= end_month):
        month_str = f"{current_m:02d}"
        yyyymm = f"{current_y}{month_str}"
        target_label = f"{current_y}-{month_str}"
        monthly_intervals.append((current_y, current_m, yyyymm, target_label))
        
        current_m += 1
        if current_m > 12:
            current_m = 1
            current_y += 1
            
    return monthly_intervals


def compute_sha256(content_bytes):
    """Computes SHA-256 hash of raw byte content for data integrity tracking."""
    return hashlib.sha256(content_bytes).hexdigest()


class IncubatorArchivalScraper:
    """
    Automated scraper for current and historical (Wayback Machine) web pages.
    """
    def __init__(self, output_root="scraped_html", request_delay=1.0, timeout=15):
        self.output_root = output_root
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (Research Scraper; Academic Study)"
        })
        self.manifest = []
        os.makedirs(self.output_root, exist_ok=True)

    def _save_html(self, file_path, content_text, metadata):
        """Saves HTML string to disk and appends to manifest."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content_text)
        
        file_bytes = content_text.encode("utf-8")
        metadata["file_path"] = file_path
        metadata["file_size_bytes"] = len(file_bytes)
        metadata["sha256"] = compute_sha256(file_bytes)
        metadata["saved_at"] = datetime.now().isoformat()
        self.manifest.append(metadata)
        logger.info(f" Saved: {file_path} ({metadata['file_size_bytes']:,} bytes)")

    def scrape_current_page(self, incubator_slug, page_type, target_url):
        """
        Scrapes the live, current version of a webpage.
        """
        out_path = os.path.join(self.output_root, incubator_slug, "current", f"{page_type}_current.html")
        
        if os.path.exists(out_path):
            logger.info(f" Skipping existing current file: {out_path}")
            return True

        logger.info(f" Fetching CURRENT [{page_type}] for {incubator_slug}: {target_url}")
        try:
            time.sleep(self.request_delay)
            resp = self.session.get(target_url, timeout=self.timeout)
            
            metadata = {
                "incubator": incubator_slug,
                "scope": "current",
                "page_type": page_type,
                "requested_url": target_url,
                "resolved_url": resp.url,
                "status_code": resp.status_code,
                "snapshot_timestamp": None,
                "month_label": "CURRENT"
            }
            
            if resp.status_code == 200:
                self._save_html(out_path, resp.text, metadata)
                return True
            else:
                logger.warning(f" Failed with HTTP {resp.status_code}: {target_url}")
                return False
        except Exception as e:
            logger.error(f" Network error scraping current {target_url}: {e}")
            return False

    def scrape_archived_page_monthly(self, incubator_slug, page_type, target_url, yyyymm, month_label, max_retries=3):
        """
        Queries the Wayback Machine for the earliest available snapshot of target_url
        in the specified YYYYMM month and saves the raw HTML.
        Implements exponential backoff on HTTP 429 to respect Internet Archive rate limits.
        Uses the `id_` flag to retrieve pure raw original HTML without Wayback UI artifacts.
        """
        file_prefix = f"{page_type}_{month_label}"
        target_dir = os.path.join(self.output_root, incubator_slug, "archived", page_type)
        os.makedirs(target_dir, exist_ok=True)
        
        # Check if already scraped for this month
        for existing_file in os.listdir(target_dir):
            if existing_file.startswith(file_prefix) and existing_file.endswith(".html"):
                logger.info(f" Snapshot for {month_label} already exists: {existing_file}")
                return True

        # Target the 1st of the month at 00:00:00 to retrieve earliest available snapshot in that month
        wb_url = f"https://web.archive.org/web/{yyyymm}01000000/{target_url}"
        logger.info(f" Querying Wayback snapshot: {month_label} for {target_url}")
        
        for attempt in range(max_retries):
            try:
                time.sleep(self.request_delay)
                head_resp = self.session.get(wb_url, timeout=self.timeout, allow_redirects=True)
                
                if head_resp.status_code == 200 and "web.archive.org/web/" in head_resp.url:
                    resolved_url = head_resp.url
                    parts = resolved_url.split("/web/")[1].split("/")
                    snapshot_ts = parts[0].replace("id_", "")
                    
                    # Fetch unmodified raw HTML with `id_` flag
                    raw_wb_url = f"https://web.archive.org/web/{snapshot_ts}id_/{target_url}"
                    time.sleep(self.request_delay * 0.5)
                    raw_resp = self.session.get(raw_wb_url, timeout=self.timeout)
                    html_content = raw_resp.text if raw_resp.status_code == 200 else head_resp.text
                    
                    out_path = os.path.join(target_dir, f"{file_prefix}_{snapshot_ts}.html")
                    metadata = {
                        "incubator": incubator_slug,
                        "scope": "archived",
                        "page_type": page_type,
                        "requested_url": target_url,
                        "wayback_url": raw_wb_url,
                        "resolved_url": resolved_url,
                        "status_code": 200,
                        "snapshot_timestamp": snapshot_ts,
                        "month_label": month_label
                    }
                    self._save_html(out_path, html_content, metadata)
                    return True
                elif head_resp.status_code == 429:
                    backoff = (attempt + 1) * 4
                    logger.warning(f" HTTP 429 Rate Limit encountered. Backing off for {backoff}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(backoff)
                    continue
                elif head_resp.status_code == 404:
                    logger.warning(f" No Wayback snapshot captured for {month_label} on {target_url}")
                    return False
                else:
                    logger.warning(f" Wayback returned HTTP {head_resp.status_code} for {month_label}")
                    return False
            except Exception as e:
                logger.error(f" Network error on Wayback query ({month_label}, attempt {attempt+1}): {e}")
                time.sleep(3)
        return False

    def save_manifest(self):
        """Exports scraping audit log to JSON and CSV."""
        json_path = os.path.join(self.output_root, "scraping_manifest.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)
        
        if self.manifest:
            import pandas as pd
            csv_path = os.path.join(self.output_root, "scraping_summary.csv")
            pd.DataFrame(self.manifest).to_csv(csv_path, index=False)
            logger.info(f" Manifest and summary saved: {json_path} & {csv_path}")


# --------------------------------------------------------------------------------------
# BATCH EXECUTION RUNNER
# --------------------------------------------------------------------------------------
def run_pipeline(incubators_to_run=None, max_months=None, delay=1.0):
    """
    Executes the complete archival scraping pipeline.
    """
    scraper = IncubatorArchivalScraper(request_delay=delay)
    monthly_intervals = generate_monthly_timestamps(2022, 1, 2026, 9)
    
    if max_months:
        monthly_intervals = monthly_intervals[:max_months]
        
    target_list = incubators_to_run or INCUBATORS
    
    logger.info("=" * 80)
    logger.info(f"STARTING SCRAPING PIPELINE: {len(target_list)} Incubators | {len(monthly_intervals)} Months")
    logger.info("=" * 80)
    
    for inc in target_list:
        slug = inc["slug"]
        logger.info(f"\n>>> PROCESSING INCUBATOR: {inc['name']} ({slug})")
        
        # 1. Scrape Current Pages
        scraper.scrape_current_page(slug, "homepage", inc["home_url"])
        scraper.scrape_current_page(slug, "about_us", inc["about_url"])
        
        # 2. Scrape Monthly Archived Pages
        for y, m, yyyymm, label in monthly_intervals:
            scraper.scrape_archived_page_monthly(slug, "homepage", inc["home_url"], yyyymm, label)
            scraper.scrape_archived_page_monthly(slug, "about_us", inc["about_url"], yyyymm, label)
            
    scraper.save_manifest()
    logger.info("\n" + "=" * 80)
    logger.info("SCRAPING PIPELINE COMPLETE!")
    logger.info("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Startup Incubator Web Archival & Current Scraper")
    parser.add_argument("--incubator", type=str, help="Specific incubator slug to scrape (e.g., t_hub)")
    parser.add_argument("--max_months", type=int, help="Limit number of monthly snapshots for testing")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests (politeness)")
    args = parser.parse_args()

    selected_incubators = None
    if args.incubator:
        selected_incubators = [i for i in INCUBATORS if i["slug"] == args.incubator]
        
    run_pipeline(incubators_to_run=selected_incubators, max_months=args.max_months, delay=args.delay)
