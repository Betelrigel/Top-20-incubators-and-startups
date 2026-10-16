# Automated Web Archival & Current Scraper for Startup Incubators

## 1. Project Overview & Research Scope

This repository provides an automated, production-grade Python 3 scraping pipeline engineered to collect **current live** and **historical monthly archived** web pages for the premier startup incubator programs in India identified in Question 1.

### Target Pages Collected:
1. **Homepage** (`/` or root URL)
2. **About Us Page** (`/about`, `/about-us`, `/who-we-are`, `/overview`)

### Archival Frequency & Longitudinal Timeline:
* **Time Horizon**: January 2022 to September 2026 (~5 calendar years / **57 monthly intervals**).
* **Sampling Cadence**: **Earliest available snapshot per calendar month** via the Internet Archive Wayback Machine CDX Server API (`collapse=timestamp:6`).
* **Content Fidelity**: Downloads pure, unmodified original HTML using Wayback's identity flag (`id_`), bypassing injected banner wrappers, toolbar styling, and third-party replay scripts.

---

## 2. Directory Hierarchy & Storage Convention

All scraped assets are organized hierarchically under `scraped_html/` by incubator slug, retention scope, and page type:

```
scraped_html/
├── scraping_manifest.json          <-- Audit trail of all scraped files with hashes
├── scraping_summary.csv           <-- Tabular CSV export of all scrape metadata
├── t_hub/
│   ├── current/
│   │   ├── homepage_current.html
│   │   └── about_us_current.html
│   └── archived/
│       ├── homepage/
│       │   ├── homepage_2022-01_20211222091258.html
│       │   ├── homepage_2022-02_20220201064105.html
│       │   └── ...
│       └── about_us/
│           ├── about_us_2022-01_20220119041201.html
│           └── ...
├── iima_ventures/
│   ├── current/
│   │   ├── homepage_current.html
│   │   └── about_us_current.html
│   └── archived/
│       ├── homepage/
│       └── about_us/
├── nsrcel_iimb/
├── iitm_incubation_cell/
├── sine_iit_bombay/
├── venture_center/
├── ccamp/
├── fitt_iit_delhi/
├── siic_iit_kanpur/
├── kerala_startup_mission/
├── bits_pieds/
├── axilor_ventures/
├── villgro/
├── ikp_knowledge_park/
└── kiit_tbi/
```

### File Naming Convention:
* **Current Pages**: `{page_type}_current.html`
* **Archived Pages**: `{page_type}_{YYYY-MM}_{WaybackTimestamp}.html`  
  *(Example: `homepage_2022-01_20211222091258.html` represents the earliest available snapshot for January 2022, captured on 2021-12-22 at 09:12:58 UTC).*

---

## 3. Installation & Prerequisites

The scraper requires **Python 3.8+** and standard networking/data manipulation packages:

```bash
# Clone or navigate to the repository directory
cd c:\Users\MARISSA\OneDrive\Desktop\RA

# Install required dependencies
python -m pip install requests pandas
```

---

## 4. Architectural Design & Engineering Mechanics

### A. Earliest-Monthly-Snapshot Discovery (CDX API)
Rather than submitting blind historical requests that trigger HTTP 302 redirect loops, the scraper queries the **Wayback Machine CDX Server API**:

```
https://web.archive.org/cdx/search/cdx?url={TARGET_URL}&from=20220101&to=20260930&output=json&fl=timestamp,original&filter=statuscode:200&collapse=timestamp:6
```

* **`collapse=timestamp:6`**: Instructs the CDX search engine to group records by the first 6 characters of the timestamp (`YYYYMM`) and return strictly the **first (earliest) snapshot** captured within each calendar month.
* **`filter=statuscode:200`**: Ensures that only healthy, successfully rendered pages are queued for download.

### B. Unmodified Raw HTML Extraction (`id_` flag)
Standard Wayback URLs inject a client-side JavaScript toolbar (`/web/YYYYMMDDhhmmss/URL`). To obtain forensic-grade HTML identical to what was served to users on that date, the script appends `id_` to the timestamp:

```
https://web.archive.org/web/{TIMESTAMP}id_/{ORIGINAL_URL}
```

This strips all Internet Archive wrappers, analytics beacons, and iframe banners.

### C. Rate-Limiting & Exponential Backoff Governance
To maintain polite, ethical crawl behavior and prevent HTTP 429 (Too Many Requests) blocking:
1. **Configurable Sleep Interval**: Enforces a polite delay (default: `2.0` seconds) between successive requests.
2. **Exponential Backoff**: If an HTTP 429 response is encountered, the scraper backs off dynamically ($4s \rightarrow 8s \rightarrow 16s$) and retries up to 3 times before logging the exception.
3. **Idempotent Resumption**: Checks for file existence prior to making network requests. If a run is interrupted, re-launching the script skips previously downloaded HTML files instantly.

---

## 5. Execution & CLI Options

### Basic Usage: Scrape All Configured Incubators
```bash
python incubator_scraper.py
```

### Targeted Execution: Scrape a Single Incubator
```bash
python incubator_scraper.py --incubator t_hub
```

### Test Mode: Limit Timeline to First N Months
```bash
python incubator_scraper.py --incubator iima_ventures --max_months 6 --delay 1.5
```

### Command-Line Arguments:
| Argument | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--incubator` | `str` | `None` | Slug of specific incubator to scrape (e.g., `t_hub`, `nsrcel_iimb`, `bits_pieds`). Omit to scrape all. |
| `--max_months` | `int` | `None` | Limits the number of monthly intervals processed (useful for rapid testing). |
| `--delay` | `float` | `2.0` | Sleep duration in seconds between network requests to prevent rate-limiting. |
| `--output` | `str` | `scraped_html` | Destination root directory for HTML files and audit manifests. |

---

## 6. Audit Manifest & Data Dictionary

Every scraped file is automatically recorded in `scraped_html/scraping_manifest.json` and `scraped_html/scraping_summary.csv`.

### Manifest Data Schema:
| Field | Type | Description | Example |
| :--- | :---: | :--- | :--- |
| `incubator` | `string` | Unique incubator identifier slug | `t_hub` |
| `scope` | `string` | `current` or `archived` | `archived` |
| `page_type` | `string` | `homepage` or `about_us` | `homepage` |
| `requested_url`| `string` | Original target URL | `https://t-hub.co` |
| `wayback_url` | `string` | Resolved raw snapshot URL | `https://web.archive.org/web/20220119001812id_/https://t-hub.co/` |
| `status_code` | `integer`| HTTP response code | `200` |
| `snapshot_timestamp` | `string` | 14-digit Wayback capture timestamp | `20220119001812` |
| `month_label` | `string` | Target calendar month label | `2022-01` |
| `file_path` | `string` | Local disk destination | `scraped_html/t_hub/archived/homepage/homepage_2022-01_20220119001812.html` |
| `file_size_bytes` | `integer`| Size of saved HTML on disk | `421183` |
| `sha256` | `string` | Cryptographic hash of content | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `saved_at` | `string` | ISO 8601 local timestamp | `2026-10-16T15:33:06.613145` |

---

## 7. Downstream Research Extensions

The collected HTML archive serves as raw input for multiple academic and venture analysis workflows:
1. **Longitudinal Text Parsing**: Extract `<title>`, `<meta description>`, and `<p>` tags across historical snapshots using `BeautifulSoup` to study shifting strategic priorities (e.g., emergence of AI/ML or Deep Tech focus).
2. **Team & Governance Tracking**: Parse leadership changes on About Us pages over the 5-year window.
3. **Cohort Milestone Extraction**: Detect announcements of new accelerator programs, government seed fund allocations, and corporate partnership expansions.
