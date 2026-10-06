"""Checks for the Python parts of the pipeline: reading SEC files, matching wordings and labelling direction."""
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import download_votes  # noqa: E402
import label_proposals  # noqa: E402

VOTE_XML = """<?xml version="1.0"?>
<inf:proxyVoteTable xmlns:inf="http://www.sec.gov/edgar/document/npxproxy/informationtable">
<inf:proxyTable><inf:issuerName>Alcoa  Corp</inf:issuerName><inf:cusip>013872106</inf:cusip>
<inf:meetingDate>07/16/2024</inf:meetingDate><inf:voteDescription>Report on climate lobbying</inf:voteDescription>
<inf:voteCategories><inf:voteCategory><inf:categoryType>ENVIRONMENT OR CLIMATE</inf:categoryType></inf:voteCategory>
<inf:voteCategory><inf:categoryType>OTHER SOCIAL ISSUES</inf:categoryType></inf:voteCategory></inf:voteCategories>
<inf:voteSource>SECURITY HOLDER</inf:voteSource><inf:sharesVoted>100</inf:sharesVoted><inf:sharesOnLoan>0</inf:sharesOnLoan>
<inf:vote><inf:voteRecord><inf:howVoted>FOR</inf:howVoted><inf:sharesVoted>60</inf:sharesVoted>
<inf:managementRecommendation>AGAINST</inf:managementRecommendation></inf:voteRecord>
<inf:voteRecord><inf:howVoted>AGAINST</inf:howVoted><inf:sharesVoted>40</inf:sharesVoted>
<inf:managementRecommendation>FOR</inf:managementRecommendation></inf:voteRecord></inf:vote>
<inf:voteSeries>S000083896</inf:voteSeries></inf:proxyTable>
</inf:proxyVoteTable>"""

COVER_XML = """<edgarSubmission xmlns="http://www.sec.gov/edgar/npx"><headerData><filerInfo>
<registrantType>RMIC</registrantType><periodOfReport>06/30/2025</periodOfReport></filerInfo></headerData>
<formData><coverPage><reportCalendarYear>2025</reportCalendarYear>
<reportInfo><reportType>FUND VOTING REPORT</reportType></reportInfo></coverPage>
<seriesPage><seriesDetails><seriesReports><idOfSeries>S000081302</idOfSeries>
<nameOfSeries>Example Sustainable ETF</nameOfSeries></seriesReports></seriesDetails></seriesPage></formData></edgarSubmission>"""


def test_vote_file_gives_one_row_per_vote_record(tmp_path):
    path = tmp_path / "table.xml"
    path.write_text(VOTE_XML, encoding="utf-8")
    out = io.StringIO()
    count = download_votes.parse_votes(path, "0001-25-000001", csv.writer(out))
    rows = list(csv.reader(io.StringIO(out.getvalue())))
    assert count == 2 and len(rows) == 2
    first = dict(zip(download_votes.VOTE_COLS, rows[0]))
    assert first["issuer_name"] == "Alcoa Corp"          # repeated spaces are tidied
    assert first["cusip"] == "013872106"                 # the leading zero survives
    assert first["categories"] == "ENVIRONMENT OR CLIMATE|OTHER SOCIAL ISSUES"
    assert first["how_voted"] == "FOR" and first["shares_voted"] == "60"
    assert first["series_id"] == "S000083896"


def test_cover_page_is_read():
    cover = download_votes.parse_cover(COVER_XML)
    assert cover["registrant_type"] == "RMIC"
    assert cover["report_type"] == "FUND VOTING REPORT"
    assert cover["report_year"] == "2025"
    assert cover["series"] == [("S000081302", "Example Sustainable ETF")]


def test_broken_cover_page_does_not_crash():
    assert download_votes.parse_cover("<not finished") is None


def test_wordings_of_the_same_proposal_look_alike_after_cleaning():
    a = label_proposals.clean_wording("6. Shareholder Proposal Regarding Report on Human Rights Due Diligence")
    b = label_proposals.clean_wording("Report on Human Rights Due Diligence (2)")
    c = label_proposals.clean_wording("Stockholder proposal requesting a report on packaging materials, if properly presented")
    assert label_proposals.similarity(a, b) >= 0.9
    assert label_proposals.similarity(a, c) < 0.5


def test_misread_ai_is_repaired():
    assert label_proposals.clean_wording("Report on Al Data Usage Oversight") == label_proposals.clean_wording("Report on AI data usage oversight")


def test_company_names_match_across_spellings():
    assert label_proposals.clean_company("THE COCA-COLA COMPANY") == label_proposals.clean_company("Coca-Cola Co.")
    assert label_proposals.clean_company("Amazon.com, Inc.") == label_proposals.clean_company("AMAZON.COM INC")


def test_direction_rules_on_clear_cases():
    assert label_proposals.rule_direction("Report on climate transition plan") == "supports ESG"
    assert label_proposals.rule_direction("Racial equity audit") == "supports ESG"
    assert label_proposals.rule_direction("Request to cease DEI efforts") == "opposes ESG"
    assert label_proposals.rule_direction("Report on risks of censorship in generative AI") == "opposes ESG"
    assert label_proposals.rule_direction("Assessment of investing in bitcoin") == "unclear"


def test_opposing_rules_are_checked_first():
    # Opposing proposals often reuse ESG vocabulary, so those rules must win when both match.
    assert label_proposals.rule_direction("Report on risks created by the company's diversity, equity and inclusion efforts") == "opposes ESG"
    assert label_proposals.rule_direction("Revisit plastics packaging policies") == "opposes ESG"
