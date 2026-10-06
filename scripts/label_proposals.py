"""Match differently worded copies of the same shareholder proposal and label which way each one points.

Input:  proposals.csv  (from export_proposals.py)
Output: proposal_labels.csv   one row per input row, with a proposal_id and a direction
        proposal_groups.csv   one row per matched proposal

Two independent signals decide the direction:
  1. the wording (keyword rules), and
  2. how a reference group of specialist ESG fund houses voted.
Where both exist, their agreement is a measure of how reliable each one is.

    python scripts/label_proposals.py
"""
import re

import pandas as pd

SUFFIXES = r"\b(the|inc|incorporated|corp|corporation|co|company|ltd|limited|plc|sa|ag|nv|se|asa|ab|as|oyj|spa|lp|llc|holdings?|group|class [abc]|cl [abc]|com|adr|n v|s a)\b"

ANTI = [
    r"censor", r"viewpoint", r"civil libert", r"de ?bank", r"politiciz", r"ideolog", r"\bcharitable\b", r"corporate giving",
    r"\broi\b", r"return on investment", r"cease (dei|cei)", r"affirmative action", r"reverse discrimination",
    r"faith based", r"religio", r"anti american", r"h 1b", r"china (entanglement|exposure)|operations in china|risk of china",
    r"gender based compensation", r"eeo policy risk", r"merchant category", r"takedown", r"impact of climate commitments",
    r"due to climate change policies", r"human rights congruency|congruency report on privacy", r"dei goals in executive pay",
    r"risks? of esg|esg and dei executive", r"delays in revising", r"dei risks", r"recruitment discrimination",
    r"advertising risks", r"financial sustainability", r"security resiliency", r"director(s)? (political and charitable|donations)|director transparency on political",
    r"financial impact of policy positions", r"voluntary carbon reduction", r"risks? (created by|arising from|of|related to) (the company s )?(dei|diversity equity|esg|net zero|decarboni|climate (commitment|goal|target))",
    r"non ?fiduciary", r"fiduciary (duty|carbon|relevance)", r"discrimination in (genai|charitable)|risks of discrimination in gen", r"gender transition|detransition|puberty",
    r"backlash|boycott", r"hiring based on merit|merit based", r"abortion (travel|risk|cost)|cost of abortion", r"election integrity|voter",
    r"unmasking|transparency in vendor|content moderation", r"brand (misalignment|damage due to dei)|pride|lgbt.* risk", r"climate (alarm|skeptic)|net zero (risk|cost)|cost(s)? of (net zero|decarbon|climate)",
    # Added after comparing the first rules with the reference votes: opposing proposals often borrow ESG vocabulary.
    r"\brevisit\b|risks? (created by|of maintaining)|objective evaluation|financial statement assumptions",
    r"return to merit|racial discrimination audit|hiring statistics|greenwashing|stakeholder capitalism|impact of oil and gas divestment",
    r"eliminat\w* .*(goals|targets|metrics)|remove dei|business performance risks|stranded asset risks|brand image|improper influence|ai bias|opposing state abortion",
    r"anti ?esg|rescind|abandon|eliminate (dei|diversity|climate)|discontinue (dei|diversity)", r"hate speech law|free speech|freedom of (expression|speech)", r"partnerships? with (planned|glsen|hrc)|human rights campaign|cei participation|corporate equality index",
]
PRO = [
    r"climate|greenhouse|\bghg\b|emission|scope 3|scope three|net zero|transition plan|paris|carbon|methane|fossil|coal\b|oil and gas|energy (supply|financing) ratio|decarbon|just transition",
    r"deforest|biodivers|nature loss|plastic|packaging|recycl|water\b|pesticide|antimicrobial|antibiotic|regenerative|circular|pollut|toxic|chemical|waste|lead sheathed|pfas|mining|tailings",
    r"animal welfare|treatment of animals|cage free|gestation|primate|animal testing",
    r"human rights|indigenous|conflict affected|cahra|forced labor|child labor|child safety|children|sexual exploitation|csam|trafficking",
    r"racial equity|civil rights audit|pay (gap|equity)|gender (and|or|racial)|racial (and|gender)|eeo 1|workforce data|harassment|non discrimination|freedom of association|collective bargaining|union",
    r"working conditions|health and safety|workplace safety|warehouse|living wage|paid sick|sick leave|arrest or incarceration|fair chance|healthcare|reproductive",
    r"lobbying|political (spending|contribution|expenditure|activit)|election cycle|tax transparency|tax practices",
    r"misinformation|disinformation|hate|antisemit|deepfake|data (privacy|usage|sourcing|collection|protection)|ai (data|oversight|board)|artificial intelligence|weapons|surveillance|facial recognition",
    r"diversity|inclusion|\bdei\b|equity audit|stakeholder|sustainab|patent|drug pricing|access to medicine|nutrition|sugar|tobacco|opioid|gun|firearm",
]


def clean_company(name):
    text = re.sub(r"[^a-z0-9 ]", " ", str(name).lower())
    text = re.sub(SUFFIXES, " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_wording(text):
    t = str(text).lower()
    t = re.sub(r"please note that this resolution is a shareholder proposal:?", " ", t)
    t = re.sub(r"\(\d+\)\s*$", " ", t)
    t = re.sub(r"^\s*(item|proposal|proposal no\.?)?\s*\d{1,2}[a-z]?[\.\):\-]?\s*", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\b(al|a i)\b", "ai", t)
    t = re.sub(r"\b(s h|sh|shp|shareholder|shareholders|shareowner|shareowners|stockholder|stockholders|security holder)\b", " ", t)
    t = re.sub(r"\b(if properly presented( at the( \d{4})?( annual)? meeting( of)?)?|at the annual meeting|non binding|advisory|properly presented)\b", " ", t)
    t = re.sub(r"\b(proposal|proposals|resolution|regarding|requesting|request|requests|relating|entitled|titled|concerning|vote|approval|approve|consider|consideration|"
               r"that|the|a|an|of|on|to|for|and|or|in|by|our|its|company|board|directors|issue|prepare|publish|produce|adopt|report|reporting|annual|additional)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def similarity(a, b):
    x, y = set(a.split()), set(b.split())
    if not x or not y:
        return 0.0
    overlap = len(x & y)
    return max(overlap / len(x | y), 0.9 * overlap / min(len(x), len(y)) if min(len(x), len(y)) >= 2 else 0)


def rule_direction(text):
    t = re.sub(r"[^a-z0-9 ]", " ", str(text).lower())
    t = re.sub(r"\b(al|a i)\b", "ai", t)
    for pattern in ANTI:
        if re.search(pattern, t):
            return "opposes ESG"
    for pattern in PRO:
        if re.search(pattern, t):
            return "supports ESG"
    return "unclear"


def main(threshold=0.5):
    # Company ID codes can start with zeros, so they must be read as text, not numbers.
    p = pd.read_csv("proposals.csv", dtype={"cusip": str, "wording_key": str, "proposal_text": str})
    p["company_key"] = p["company"].map(clean_company)
    p["meeting_key"] = p["company_key"] + "|" + p["meeting_date"].fillna("")
    p["wording"] = p["proposal_text"].map(clean_wording)

    # Match wordings inside each company meeting: most-voted wording first,
    # each later wording joins the closest existing group or starts a new one.
    group_ids = {}
    for meeting, rows in p.sort_values("fund_votes", ascending=False).groupby("meeting_key", sort=False):
        heads = []
        for index, wording in zip(rows.index, rows["wording"]):
            best, best_score = None, 0.0
            for head_number, head in enumerate(heads):
                score = similarity(wording, head)
                if score > best_score:
                    best, best_score = head_number, score
            if best is None or best_score < threshold:
                heads.append(wording)
                best = len(heads) - 1
            group_ids[index] = f"{meeting}|{best + 1}"
    p["proposal_id"] = pd.Series(group_ids)

    def summarise(g):
        top = g.sort_values("fund_votes", ascending=False).iloc[0]
        return pd.Series({
            "company": top["company"], "meeting_date": top["meeting_date"], "report_year": top["report_year"],
            "title": top["proposal_text"], "wordings": len(g), "all_wordings": " || ".join(g["proposal_text"].astype(str).unique()[:12]),
            "fund_votes": g["fund_votes"].sum(), "fund_votes_for": g["fund_votes_for"].sum(),
            "esg_votes": g["esg_votes"].sum(), "esg_votes_for": g["esg_votes_for"].sum(),
            "reference_votes": g["reference_votes"].sum(), "reference_votes_for": g["reference_votes_for"].sum(),
            "is_environment": bool(g["is_environment"].any()), "is_social": bool(g["is_social"].any()),
        })

    groups = p.groupby("proposal_id").apply(summarise, include_groups=False).reset_index()
    groups["pct_for"] = (100 * groups["fund_votes_for"] / groups["fund_votes"]).round(1)
    groups["reference_pct_for"] = (100 * groups["reference_votes_for"] / groups["reference_votes"]).round(1)
    groups["by_wording"] = groups["all_wordings"].map(rule_direction)

    def by_reference(row):
        if row["reference_votes"] < 3:
            return "not enough votes"
        if row["reference_pct_for"] >= 60:
            return "supports ESG"
        if row["reference_pct_for"] <= 15:
            return "opposes ESG"
        return "unclear"

    groups["by_reference_votes"] = groups.apply(by_reference, axis=1)

    def final(row):
        """The reference votes decide when there are enough of them; otherwise the wording does."""
        reference = row["by_reference_votes"]
        if reference in ("supports ESG", "opposes ESG"):
            return pd.Series([reference, "reference votes"])
        if reference == "unclear":
            return pd.Series(["split", "reference votes"])
        return pd.Series([row["by_wording"], "wording only"])

    groups[["direction", "basis"]] = groups.apply(final, axis=1)
    groups.sort_values("fund_votes", ascending=False).to_csv("proposal_groups.csv", index=False)
    p.merge(groups[["proposal_id", "direction", "basis"]], on="proposal_id")[
        ["cusip", "meeting_date", "report_year", "wording_key", "proposal_id", "direction", "basis"]
    ].to_csv("proposal_labels.csv", index=False)
    return p, groups


if __name__ == "__main__":
    rows, groups = main()
    print(f"{len(rows):,} wordings matched into {len(groups):,} proposals")
    both = groups[groups["by_reference_votes"].isin(["supports ESG", "opposes ESG"]) & (groups["by_wording"] != "unclear")]
    agree = (both["by_wording"] == both["by_reference_votes"]).mean()
    print(f"Where both signals give an answer ({len(both):,} proposals), they agree {agree:.1%} of the time")
    print(pd.crosstab(groups["by_wording"], groups["by_reference_votes"], margins=True))
    summary = groups.groupby(["basis", "direction"]).agg(proposals=("fund_votes", "size"), fund_votes=("fund_votes", "sum"))
    summary["share_of_votes"] = (100 * summary["fund_votes"] / groups["fund_votes"].sum()).round(1)
    print(summary)
