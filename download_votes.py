"""Download every structured voting record (SEC Form N-PX) since mid-2024 and save them as compact tables.

Covers three reporting years (filed 2024, 2025 and 2026), funds and investment managers, including amendments.

Run on your own computer:
    pip install requests
    python download_votes.py --test     (a short trial, about 10 minutes)
    python download_votes.py            (the full run; expect a day or more, safe to stop and restart)

It can be stopped and started again at any time. It skips what is already done.

What it produces in the folder npx_data:
    filings.csv      one row per filing (who filed, what kind of report)
    series.csv       one row per fund inside a filing (the fund's name)
    votes/*.csv.gz   one file per fund filing, one row per vote
    log.txt          anything that went wrong
"""
import csv
import gzip
import json
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

def quarters_to_date(start=(2024, 3)):
    """Every quarter from the first structured N-PX filings up to the current quarter."""
    from datetime import date
    today = date.today()
    now = (today.year, (today.month - 1) // 3 + 1)
    year, quarter, out = start[0], start[1], []
    while (year, quarter) <= now:
        out.append((year, quarter))
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
    return out


QUARTERS = quarters_to_date()
INDEX = "https://www.sec.gov/Archives/edgar/full-index/{}/QTR{}/form.idx"
BASE = "https://www.sec.gov/Archives/"
OUT = Path("npx_data")
VOTES = OUT / "votes"
TMP = OUT / "tmp"
PAUSE = 0.15  # seconds between requests; the SEC allows at most 10 per second

FILING_COLS = ["accession", "form_type", "cik", "company", "date_filed", "registrant_type", "report_type",
               "period_of_report", "report_year", "series_count", "status"]
SERIES_COLS = ["accession", "series_id", "series_name"]
VOTE_COLS = ["accession", "issuer_name", "cusip", "isin", "meeting_date", "vote_description", "categories",
             "vote_source", "shares_voted_total", "shares_on_loan", "how_voted", "shares_voted",
             "management_recommendation", "series_id", "other_info"]


def log(message):
    with open(OUT / "log.txt", "a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")


def local(tag):
    return tag.rsplit("}", 1)[-1]


def clean(text):
    return re.sub(r"\s+", " ", text).strip() if text else ""


def get(session, url, stream=False):
    """Fetch a URL, waiting and retrying if the SEC asks us to slow down."""
    for attempt in range(6):
        try:
            time.sleep(PAUSE)
            response = session.get(url, timeout=120, stream=stream)
            if response.status_code == 200:
                return response
            if response.status_code == 404:
                return None
            wait = 60 if response.status_code in (403, 429) else 5 * (attempt + 1)
        except requests.RequestException:
            wait = 10 * (attempt + 1)
        print(f"    waiting {wait}s and trying again...")
        time.sleep(wait)
    return None


def parse_cover(xml_text):
    """Read the cover page: what kind of filer and report this is, and the funds it covers."""
    info = {"registrant_type": "", "report_type": "", "period_of_report": "", "report_year": "", "series": []}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    series_id = None
    for element in root.iter():
        tag, text = local(element.tag), clean(element.text)
        if tag == "registrantType":
            info["registrant_type"] = text
        elif tag == "reportType":
            info["report_type"] = text
        elif tag == "periodOfReport":
            info["period_of_report"] = text
        elif tag == "reportCalendarYear":
            info["report_year"] = text
        elif tag == "idOfSeries":
            series_id = text
        elif tag == "nameOfSeries" and series_id:
            info["series"].append((series_id, text))
            series_id = None
    return info


def parse_votes(path, accession, writer):
    """Read a voting table file piece by piece and write one row per vote. Returns the row count."""
    rows = 0
    for _, element in ET.iterparse(path, events=("end",)):
        if local(element.tag) != "proxyTable":
            continue
        fields = {"categories": [], "records": []}
        for child in element:
            tag = local(child.tag)
            if tag == "voteCategories":
                fields["categories"] = [clean(c.text) for c in child.iter() if local(c.tag) == "categoryType" and clean(c.text)]
            elif tag == "vote":
                for record in child:
                    if local(record.tag) == "voteRecord":
                        fields["records"].append({local(x.tag): clean(x.text) for x in record})
            elif tag != "voteManager":
                fields[tag] = clean(child.text)
        for record in fields["records"] or [{}]:
            writer.writerow([
                accession, fields.get("issuerName", ""), fields.get("cusip", ""), fields.get("isin", ""),
                fields.get("meetingDate", ""), fields.get("voteDescription", ""), "|".join(fields["categories"]),
                fields.get("voteSource", ""), fields.get("sharesVoted", ""), fields.get("sharesOnLoan", ""),
                record.get("howVoted", ""), record.get("sharesVoted", ""), record.get("managementRecommendation", ""),
                fields.get("voteSeries", ""), fields.get("voteOtherInfo", ""),
            ])
            rows += 1
        element.clear()
    return rows


def read_done():
    done = {}
    path = OUT / "filings.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                done[row["accession"]] = row
    return done


def main():
    test = "--test" in sys.argv
    OUT.mkdir(exist_ok=True)
    VOTES.mkdir(exist_ok=True)
    TMP.mkdir(exist_ok=True)
    email_file = OUT / "email.txt"
    if email_file.exists():
        email = email_file.read_text().strip()
    else:
        email = input("The SEC asks every program to give a contact email. Type yours and press Enter: ").strip()
        email_file.write_text(email)
    session = requests.Session()
    session.headers.update({"User-Agent": f"Personal research {email}", "Accept-Encoding": "gzip, deflate"})

    print("Reading the lists of filings...")
    filings = []
    for year, quarter in QUARTERS:
        response = get(session, INDEX.format(year, quarter))
        if response is None:
            print(f"  {year} quarter {quarter}: no list available")
            continue
        count = 0
        for line in response.text.splitlines():
            if line.startswith("N-PX ") or line.startswith("N-PX/A "):
                parts = re.split(r"\s{2,}", line.strip())
                if len(parts) >= 5:
                    filings.append({"form_type": parts[0], "company": parts[1], "cik": parts[2],
                                    "date_filed": parts[3], "accession": Path(parts[4]).stem})
                    count += 1
        print(f"  {year} quarter {quarter}: {count:,} filings")
    if not filings:
        print("Could not read any list from the SEC. Try again in a few minutes.")
        return
    if test:
        filings = filings[:: max(1, len(filings) // 250)]
    print(f"{len(filings):,} filings to look at." + ("  (trial run)" if test else ""))

    done = read_done()
    new_file = not (OUT / "filings.csv").exists()
    filings_handle = open(OUT / "filings.csv", "a", newline="", encoding="utf-8")
    series_handle = open(OUT / "series.csv", "a", newline="", encoding="utf-8")
    filings_writer, series_writer = csv.writer(filings_handle), csv.writer(series_handle)
    if new_file:
        filings_writer.writerow(FILING_COLS)
        series_writer.writerow(SERIES_COLS)

    started, total_votes, fund_reports = time.time(), 0, 0
    for number, filing in enumerate(filings, 1):
        accession = filing["accession"]
        if accession in done:
            continue
        folder = f"{BASE}edgar/data/{filing['cik']}/{accession.replace('-', '')}/"
        status, cover = "ok", None
        response = get(session, folder + "primary_doc.xml")
        if response is not None:
            cover = parse_cover(response.text)
        if cover is None:
            cover = {"registrant_type": "", "report_type": "", "period_of_report": "", "report_year": "", "series": []}
            status = "no cover page"

        has_votes = "VOTING" in cover["report_type"].upper()
        if has_votes:
            listing = get(session, folder + "index.json")
            items = listing.json().get("directory", {}).get("item", []) if listing is not None else []
            tables = [i["name"] for i in items if i["name"].lower().endswith(".xml") and i["name"] != "primary_doc.xml"]
            target = VOTES / f"{accession}.csv.gz"
            part = VOTES / f"{accession}.part"
            rows = 0
            try:
                with gzip.open(part, "wt", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(VOTE_COLS)
                    for name in tables:
                        download = get(session, folder + name, stream=True)
                        if download is None:
                            status = "a table failed to download"
                            continue
                        temp = TMP / "table.xml"
                        with open(temp, "wb") as raw:
                            shutil.copyfileobj(_chunks(download), raw)
                        try:
                            rows += parse_votes(temp, accession, writer)
                        except ET.ParseError as error:
                            status = "a table could not be read"
                            log(f"{accession} {name}: {error}")
                        temp.unlink(missing_ok=True)
                part.replace(target)
            except Exception as error:  # keep the run alive whatever one filing does
                status = "failed"
                log(f"{accession}: {error!r}")
                part.unlink(missing_ok=True)
            total_votes += rows
            fund_reports += 1
            for series_id, series_name in cover["series"]:
                series_writer.writerow([accession, series_id, series_name])
            print(f"{number:>6}/{len(filings)}  {filing['company'][:42]:<42} {rows:>10,} votes")

        filings_writer.writerow([accession, filing["form_type"], filing["cik"], filing["company"], filing["date_filed"],
                                 cover["registrant_type"], cover["report_type"], cover["period_of_report"],
                                 cover["report_year"], len(cover["series"]), status])
        filings_handle.flush()
        series_handle.flush()
        if number % 200 == 0:
            minutes = (time.time() - started) / 60
            print(f"--- {number:,} of {len(filings):,} looked at, {fund_reports:,} voting reports, "
                  f"{total_votes:,} votes saved, {minutes:.0f} minutes so far")

    filings_handle.close()
    series_handle.close()
    size = sum(f.stat().st_size for f in VOTES.glob("*.csv.gz")) / 1e6
    summary = {"filings_seen": len(read_done()), "voting_reports_this_run": fund_reports,
               "votes_this_run": total_votes, "votes_folder_mb": round(size, 1)}
    print("\nFinished.", json.dumps(summary))
    print("Copy the 'Finished' line above and send it.")


class _chunks:
    """Lets a streamed download be copied to disk in pieces, with compression handled."""

    def __init__(self, response):
        self.iterator = response.iter_content(chunk_size=1 << 20)
        self.buffer = b""

    def read(self, size=-1):
        while size < 0 or len(self.buffer) < size:
            piece = next(self.iterator, None)
            if piece is None:
                break
            self.buffer += piece
        if size < 0:
            data, self.buffer = self.buffer, b""
        else:
            data, self.buffer = self.buffer[:size], self.buffer[size:]
        return data


if __name__ == "__main__":
    main()
