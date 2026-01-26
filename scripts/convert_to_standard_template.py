"""
Convert all equity reports to the standardized dark theme template.
This script extracts content from existing reports and applies the canonical template styling.
"""

import os
import re
from datetime import datetime

# Standardized CSS - matches templates/equity_report_template.html
STANDARDIZED_CSS = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            color: #c9d1d9;
            line-height: 1.7;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 30px; }

        /* Header */
        .header {
            background: linear-gradient(135deg, #1f3a5c 0%, #21262d 100%);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
        }
        .header-left h1 { color: #58a6ff; font-size: 3em; margin-bottom: 10px; }
        .header-left h2 { color: #c9d1d9; font-size: 1.4em; font-weight: 400; margin-bottom: 15px; }
        .header-left .sector { color: #8b949e; font-size: 1.1em; }
        .header-left .date { color: #6e7681; margin-top: 15px; }

        .header-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: center;
        }
        .rating-badge {
            padding: 15px 40px;
            border-radius: 8px;
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 20px;
            color: white;
        }
        .rating-badge.buy { background: #238636; }
        .rating-badge.hold { background: #9e6a03; }
        .rating-badge.sell { background: #da3633; }

        .price-info { text-align: right; }
        .price-info .current { font-size: 2em; color: #58a6ff; }
        .price-info .target { color: #3fb950; font-size: 1.2em; margin-top: 5px; }
        .price-info .upside { color: #8b949e; }
        .price-info .upside.positive { color: #3fb950; }
        .price-info .upside.negative { color: #f85149; }

        /* Key Metrics Strip */
        .metrics-strip {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .metric-box {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .metric-box .label { color: #8b949e; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric-box .value { color: #58a6ff; font-size: 1.6em; font-weight: bold; margin-top: 8px; }
        .metric-box .value.positive { color: #3fb950; }
        .metric-box .value.negative { color: #f85149; }
        .metric-box .change { font-size: 0.85em; margin-top: 5px; color: #8b949e; }
        .metric-box .change.positive { color: #3fb950; }
        .metric-box .change.negative { color: #f85149; }

        /* Section Styling */
        section {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 16px;
            padding: 35px;
            margin-bottom: 25px;
        }
        section h2 {
            color: #58a6ff;
            font-size: 1.6em;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #30363d;
        }
        section h3 { color: #c9d1d9; font-size: 1.25em; margin: 25px 0 15px; }
        section h4 { color: #8b949e; font-size: 1.05em; margin: 20px 0 12px; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid #30363d; }
        th { background: #21262d; color: #58a6ff; font-weight: 600; font-size: 0.9em; text-transform: uppercase; }
        tr:hover { background: rgba(88, 166, 255, 0.05); }
        .text-right { text-align: right; }
        .text-center { text-align: center; }
        .total-row { background: #21262d; font-weight: bold; }

        /* Highlight Boxes */
        .highlight-box {
            background: linear-gradient(135deg, #1f3a5c 0%, #1a2733 100%);
            border-left: 4px solid #58a6ff;
            padding: 25px;
            border-radius: 0 12px 12px 0;
            margin: 20px 0;
        }
        .highlight-box.warning { border-left-color: #9e6a03; }
        .highlight-box.success { border-left-color: #3fb950; }
        .highlight-box.danger { border-left-color: #f85149; }

        /* Scenario Cards */
        .scenarios-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 25px 0; }
        .scenario-card {
            background: #21262d;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border-top: 4px solid;
        }
        .scenario-card.super-bear { border-color: #da3633; }
        .scenario-card.bear { border-color: #f85149; }
        .scenario-card.base { border-color: #58a6ff; }
        .scenario-card.bull { border-color: #3fb950; }
        .scenario-card.super-bull { border-color: #238636; }
        .scenario-card .name { font-weight: bold; color: #c9d1d9; margin-bottom: 8px; }
        .scenario-card .prob { color: #8b949e; font-size: 0.9em; margin-bottom: 12px; }
        .scenario-card .value { font-size: 1.5em; font-weight: bold; }
        .scenario-card .contribution { color: #8b949e; font-size: 0.85em; margin-top: 8px; }

        /* Valuation Table */
        .valuation-table { font-size: 0.95em; }
        .valuation-table th, .valuation-table td { padding: 12px 14px; text-align: center; }
        .valuation-table th { background: #21262d; color: #58a6ff; }
        .valuation-table .scenario-super-bear { color: #f85149; font-weight: bold; }
        .valuation-table .scenario-bear { color: #ffa657; }
        .valuation-table .scenario-base { color: #58a6ff; font-weight: bold; }
        .valuation-table .scenario-bull { color: #3fb950; }
        .valuation-table .scenario-super-bull { color: #238636; font-weight: bold; }

        /* Probability Weighted Box */
        .probability-weighted {
            background: linear-gradient(135deg, #1f3a5c 0%, #1a2733 100%);
            padding: 25px;
            border-radius: 12px;
            margin: 25px 0;
            text-align: center;
            border: 1px solid #30363d;
        }
        .probability-weighted h3 { color: #58a6ff; margin-bottom: 15px; }
        .probability-weighted .value { font-size: 2.5em; font-weight: bold; color: #3fb950; }

        /* Debate Log */
        .debate-log {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            background: #0d1117;
        }
        .debate-message {
            margin-bottom: 15px;
            padding: 18px;
            border-radius: 10px;
            background: #161b22;
            border-left: 4px solid;
        }
        .debate-message.analyst { border-left-color: #58a6ff; }
        .debate-message.bull { border-left-color: #3fb950; }
        .debate-message.bear { border-left-color: #f85149; }
        .debate-message.critic { border-left-color: #ffa657; }
        .debate-message.synthesizer { border-left-color: #a371f7; }
        .debate-message .role {
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.8em;
            margin-bottom: 8px;
            letter-spacing: 0.5px;
        }
        .debate-message.analyst .role { color: #58a6ff; }
        .debate-message.bull .role { color: #3fb950; }
        .debate-message.bear .role { color: #f85149; }
        .debate-message.critic .role { color: #ffa657; }
        .debate-message.synthesizer .role { color: #a371f7; }
        .debate-message .content { color: #c9d1d9; line-height: 1.6; }

        /* Section Content */
        .section-content {
            white-space: pre-wrap;
            font-size: 0.95rem;
            line-height: 1.8;
            color: #c9d1d9;
        }

        /* Navigation */
        .nav-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #58a6ff;
            text-decoration: none;
            font-size: 0.95em;
        }
        .nav-link:hover { text-decoration: underline; }

        /* Footer */
        footer {
            text-align: center;
            padding: 30px;
            color: #6e7681;
            font-size: 0.9em;
            border-top: 1px solid #30363d;
            margin-top: 30px;
        }

        /* Responsive */
        @media (max-width: 1200px) {
            .scenarios-grid { grid-template-columns: repeat(3, 1fr); }
            .metrics-strip { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 768px) {
            .header { grid-template-columns: 1fr; }
            .scenarios-grid { grid-template-columns: 1fr 1fr; }
            .metrics-strip { grid-template-columns: 1fr 1fr; }
        }
"""

def extract_content_between_tags(html, start_marker, end_marker):
    """Extract content between two markers in HTML"""
    start_idx = html.find(start_marker)
    if start_idx == -1:
        return ""
    start_idx += len(start_marker)
    end_idx = html.find(end_marker, start_idx)
    if end_idx == -1:
        return html[start_idx:]
    return html[start_idx:end_idx]

def extract_section_content(html, section_title):
    """Extract content from a section by its h2 title"""
    pattern = rf'<h2>{re.escape(section_title)}</h2>\s*<div class="section-content">(.*?)</div>\s*</section>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_valuation_table(html):
    """Extract the valuation table HTML"""
    pattern = r'<table class="valuation-table">(.*?)</table>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        return match.group(0)
    return ""

def extract_probability_weighted_value(html):
    """Extract the probability-weighted fair value"""
    pattern = r'<div class="value">\$?([\d.]+)</div>'
    match = re.search(pattern, html)
    if match:
        return match.group(1)
    return "N/A"

def extract_debate_log(html):
    """Extract the debate log HTML"""
    pattern = r'<div class="debate-log">(.*?)</div>\s*</section>'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_meta_info(html):
    """Extract ticker, company name, sector, industry from header"""
    ticker_match = re.search(r'<h1>([^<]+)', html)
    ticker = ticker_match.group(1).strip() if ticker_match else "UNKNOWN"

    subtitle_match = re.search(r'<div class="subtitle">([^<]+)', html)
    company = subtitle_match.group(1).strip() if subtitle_match else "Unknown Company"

    sector_match = re.search(r'Sector:\s*([^<]+)', html)
    sector = sector_match.group(1).strip() if sector_match else "Unknown"

    industry_match = re.search(r'Industry:\s*([^<]+)', html)
    industry = industry_match.group(1).strip() if industry_match else "Unknown"

    return ticker, company, sector, industry

def convert_report_to_standard(input_path, output_path):
    """Convert a single report to the standardized template"""
    with open(input_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Extract all components
    ticker, company, sector, industry = extract_meta_info(html)
    ticker_clean = ticker.replace('<span class="arch-badge">Hierarchical v2.0</span>', '').strip()

    executive_summary = extract_section_content(html, "Executive Summary")
    industry_analysis = extract_section_content(html, "Industry Analysis")
    company_analysis = extract_section_content(html, "Company Analysis")
    corporate_governance = extract_section_content(html, "Corporate Governance")

    valuation_table = extract_valuation_table(html)
    pwv = extract_probability_weighted_value(html)
    debate_log = extract_debate_log(html)

    # Determine currency based on ticker
    if "US" in ticker_clean or "US" in input_path:
        currency = "USD"
    elif "CH" in ticker_clean:
        currency = "CNY"
    else:
        currency = "HKD"

    # Build the standardized report
    report_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker_clean} - {company} | Equity Research Report</title>
    <style>{STANDARDIZED_CSS}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-left">
                <h1>{ticker_clean}</h1>
                <h2>{company}</h2>
                <p class="sector">{sector} | {industry}</p>
                <p class="date">Valuation Date: {datetime.now().strftime("%Y-%m-%d")}</p>
            </div>
            <div class="header-right">
                <div class="rating-badge hold">HOLD</div>
                <div class="price-info">
                    <div class="target">Fair Value: {currency} {pwv}</div>
                    <div class="upside">Probability-Weighted</div>
                </div>
            </div>
        </header>

        <a href="index.html" class="nav-link">&larr; Back to Index</a>

        <!-- Executive Summary -->
        <section>
            <h2>Executive Summary</h2>
            <div class="section-content">{executive_summary}</div>
        </section>

        <!-- Valuation Summary -->
        <section>
            <h2>Valuation Summary</h2>
            <h3>Scenario-Based Intrinsic Values</h3>
            {valuation_table}

            <div class="probability-weighted">
                <h3>Probability-Weighted Fair Value</h3>
                <div class="value">{currency} {pwv}</div>
            </div>
        </section>

        <!-- Industry Analysis -->
        <section>
            <h2>Industry Analysis</h2>
            <div class="section-content">{industry_analysis}</div>
        </section>

        <!-- Company Analysis -->
        <section>
            <h2>Company Analysis</h2>
            <div class="section-content">{company_analysis}</div>
        </section>

        <!-- Corporate Governance -->
        <section>
            <h2>Corporate Governance</h2>
            <div class="section-content">{corporate_governance}</div>
        </section>

        <!-- Multi-Agent Debate Log -->
        <section>
            <h2>Multi-Agent Debate Log (10 Rounds)</h2>
            <div class="debate-log">
                {debate_log}
            </div>
        </section>

        <!-- Footer -->
        <footer>
            <p>Multi-AI Equity Research System | Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
            <p>This report is for informational purposes only and does not constitute investment advice.</p>
            <p>Hierarchical Agent Architecture: Architects → Supervisors → Workers → Goalkeepers</p>
        </footer>
    </div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_html)

    print(f"Converted: {ticker_clean}")
    return ticker_clean, company, pwv, currency

def main():
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

    # List of reports to convert (using the simple filenames)
    reports_to_convert = [
        "LEGN_US.html",
        "9660_HK.html",
        "9926_HK.html",
        "762_HK.html",
        "1799_HK.html",
        "3888_HK.html",
        "3800_HK.html",
        "1045_HK.html",
        "2696_HK.html",
        "9969_HK.html",
        "3319_HK.html",
        "2869_HK.html",
        "1816_HK.html",
        "600900_CH.html",
        "VST_US.html",
        "CEG_US.html",
        "388_HK.html",
        "JPM_US.html",
        "3968_HK.html",
    ]

    converted = []
    for filename in reports_to_convert:
        input_path = os.path.join(reports_dir, filename)
        if os.path.exists(input_path):
            output_path = input_path  # Overwrite in place
            result = convert_report_to_standard(input_path, output_path)
            converted.append(result)
        else:
            print(f"Not found: {filename}")

    print(f"\nConverted {len(converted)} reports to standardized template")
    return converted

if __name__ == "__main__":
    main()
