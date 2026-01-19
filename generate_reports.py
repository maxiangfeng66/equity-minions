"""
HTML Report Generator
Generates professional equity research HTML reports from debate JSON files
"""

import json
import os
from datetime import datetime


def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_equity_html(debate_data, research_data):
    """Generate HTML report for a single equity"""

    ticker = debate_data.get('ticker', research_data.get('ticker', 'Unknown'))
    company = debate_data.get('company', research_data.get('company', 'Unknown'))

    # Extract key data
    recommendation = debate_data.get('recommendation', debate_data.get('final_recommendation', {}).get('rating', 'N/A'))
    if isinstance(recommendation, dict):
        recommendation = recommendation.get('rating', 'HOLD')

    conviction = debate_data.get('conviction', debate_data.get('final_recommendation', {}).get('conviction', 'MEDIUM'))
    if isinstance(conviction, dict):
        conviction = conviction.get('level', 'MEDIUM')

    current_price = debate_data.get('current_price_hkd', debate_data.get('current_price', research_data.get('current_price', 0)))

    # Get valuation range
    valuation = debate_data.get('valuation_range', debate_data.get('final_recommendation', {}).get('valuation', {}))
    if isinstance(valuation, dict):
        bear_case = valuation.get('bear_case', valuation.get('bear', 0))
        base_case = valuation.get('base_case', valuation.get('base', 0))
        bull_case = valuation.get('bull_case', valuation.get('bull', 0))
    else:
        bear_case = base_case = bull_case = 0

    prob_weighted = debate_data.get('probability_weighted_price',
                   debate_data.get('final_recommendation', {}).get('probability_weighted_price', base_case))

    # Investment thesis
    thesis = debate_data.get('investment_thesis', {})
    if isinstance(thesis, str):
        summary = thesis
        bull_summary = ""
        bear_summary = ""
    else:
        summary = thesis.get('summary', '')
        bull_summary = thesis.get('bull_case_summary', '')
        bear_summary = thesis.get('bear_case_summary', '')

    # Risks and catalysts
    risks = debate_data.get('risks', debate_data.get('key_risks', []))
    catalysts = debate_data.get('catalysts', {})
    if isinstance(catalysts, dict):
        catalysts = catalysts.get('top_3_catalysts', [])

    # Debate rounds
    debate_rounds = debate_data.get('debate_rounds', [])

    # Color coding for recommendation
    rec_colors = {
        'BUY': '#28a745',
        'STRONG BUY': '#155724',
        'MODERATE BUY': '#5cb85c',
        'HOLD': '#ffc107',
        'SELL': '#dc3545',
        'STRONG SELL': '#721c24'
    }
    rec_color = rec_colors.get(str(recommendation).upper(), '#6c757d')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} - {company} | Equity Research</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .ticker {{
            font-size: 3rem;
            font-weight: 700;
            color: #00d9ff;
            letter-spacing: 2px;
        }}
        .company-name {{
            font-size: 1.5rem;
            color: #94a3b8;
            margin-top: 5px;
        }}
        .recommendation-badge {{
            display: inline-block;
            background: {rec_color};
            color: white;
            padding: 10px 25px;
            border-radius: 25px;
            font-weight: 700;
            font-size: 1.2rem;
            margin-top: 15px;
        }}
        .conviction {{
            display: inline-block;
            background: rgba(255,255,255,0.1);
            color: #ffc107;
            padding: 8px 20px;
            border-radius: 20px;
            margin-left: 10px;
            font-weight: 600;
        }}
        .price-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-top: 25px;
        }}
        .price-box {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .price-label {{
            font-size: 0.85rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .price-value {{
            font-size: 1.8rem;
            font-weight: 700;
            margin-top: 5px;
        }}
        .current {{ color: #e0e0e0; }}
        .bear {{ color: #ef4444; }}
        .base {{ color: #fbbf24; }}
        .bull {{ color: #22c55e; }}
        .target {{ color: #00d9ff; }}

        .section {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #00d9ff;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .thesis-text {{
            line-height: 1.8;
            color: #d1d5db;
        }}

        .debate-round {{
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }}
        .round-header {{
            font-weight: 600;
            color: #fbbf24;
            margin-bottom: 10px;
        }}
        .debate-role {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 8px;
        }}
        .role-bull {{ background: #166534; color: #86efac; }}
        .role-bear {{ background: #991b1b; color: #fca5a5; }}
        .role-critic {{ background: #854d0e; color: #fde047; }}
        .role-synthesizer {{ background: #1e3a5f; color: #93c5fd; }}

        .argument {{
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }}
        .argument-text {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: #d1d5db;
        }}

        .risk-item, .catalyst-item {{
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }}
        .risk-title {{
            color: #ef4444;
            font-weight: 600;
        }}
        .catalyst-title {{
            color: #22c55e;
            font-weight: 600;
        }}

        .back-link {{
            display: inline-block;
            color: #00d9ff;
            text-decoration: none;
            margin-bottom: 20px;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            color: #64748b;
            font-size: 0.9rem;
        }}

        .two-col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .two-col, .price-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">&larr; Back to Portfolio</a>

        <div class="header">
            <div class="ticker">{ticker}</div>
            <div class="company-name">{company}</div>
            <div>
                <span class="recommendation-badge">{recommendation}</span>
                <span class="conviction">Conviction: {conviction}</span>
            </div>
            <div class="price-grid">
                <div class="price-box">
                    <div class="price-label">Current Price</div>
                    <div class="price-value current">${current_price:.2f}</div>
                </div>
                <div class="price-box">
                    <div class="price-label">Bear Case</div>
                    <div class="price-value bear">${bear_case:.2f}</div>
                </div>
                <div class="price-box">
                    <div class="price-label">Base Case</div>
                    <div class="price-value base">${base_case:.2f}</div>
                </div>
                <div class="price-box">
                    <div class="price-label">Bull Case</div>
                    <div class="price-value bull">${bull_case:.2f}</div>
                </div>
            </div>
            <div class="price-grid" style="grid-template-columns: 1fr; margin-top: 10px;">
                <div class="price-box">
                    <div class="price-label">Probability-Weighted Target</div>
                    <div class="price-value target">${prob_weighted:.2f}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Investment Thesis</div>
            <p class="thesis-text">{summary}</p>
        </div>

        <div class="two-col">
            <div class="section">
                <div class="section-title">Bull Case</div>
                <p class="thesis-text">{bull_summary}</p>
            </div>
            <div class="section">
                <div class="section-title">Bear Case</div>
                <p class="thesis-text">{bear_summary}</p>
            </div>
        </div>
'''

    # Add risks section
    html += '''
        <div class="section">
            <div class="section-title">Key Risks</div>
'''
    if isinstance(risks, list):
        for risk in risks[:5]:
            if isinstance(risk, dict):
                risk_title = risk.get('risk', risk.get('title', 'Risk'))
                risk_desc = risk.get('description', risk.get('desc', ''))
            else:
                risk_title = str(risk)
                risk_desc = ''
            html += f'''
            <div class="risk-item">
                <div class="risk-title">{risk_title}</div>
                <div class="argument-text">{risk_desc}</div>
            </div>
'''
    html += '        </div>\n'

    # Add catalysts section
    html += '''
        <div class="section">
            <div class="section-title">Key Catalysts</div>
'''
    if isinstance(catalysts, list):
        for cat in catalysts[:5]:
            if isinstance(cat, dict):
                cat_title = cat.get('catalyst', cat.get('title', 'Catalyst'))
                cat_desc = cat.get('description', cat.get('desc', ''))
            else:
                cat_title = str(cat)
                cat_desc = ''
            html += f'''
            <div class="catalyst-item">
                <div class="catalyst-title">{cat_title}</div>
                <div class="argument-text">{cat_desc}</div>
            </div>
'''
    html += '        </div>\n'

    # Add debate rounds
    html += '''
        <div class="section">
            <div class="section-title">Multi-AI Debate Log</div>
'''
    for round_data in debate_rounds[:5]:
        round_num = round_data.get('round', 0)
        theme = round_data.get('theme', '')
        exchanges = round_data.get('exchanges', [])

        html += f'''
            <div class="debate-round">
                <div class="round-header">Round {round_num}: {theme}</div>
'''
        for exchange in exchanges:
            role = exchange.get('role', 'Unknown')
            argument = exchange.get('argument', exchange.get('synthesis', ''))
            role_class = f"role-{role.lower()}"
            html += f'''
                <div class="argument">
                    <span class="debate-role {role_class}">{role}</span>
                    <div class="argument-text">{argument[:800]}{'...' if len(argument) > 800 else ''}</div>
                </div>
'''
        html += '            </div>\n'

    html += '''        </div>

        <div class="footer">
            <p>Generated by Equity Research Multi-Agent System</p>
            <p>Powered by Claude, GPT, Gemini, Grok, Qwen</p>
            <p>''' + datetime.now().strftime('%Y-%m-%d %H:%M') + '''</p>
        </div>
    </div>
</body>
</html>'''

    return html


def generate_index_html(all_equities):
    """Generate index page with all equities"""

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Portfolio | Multi-AI Analysis</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 30px;
        }
        .main-title {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            color: #94a3b8;
            margin-top: 10px;
            font-size: 1.1rem;
        }
        .ai-badges {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .ai-badge {
            background: rgba(255,255,255,0.1);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #94a3b8;
        }

        .equity-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .equity-card {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 25px;
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .equity-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            background: rgba(255,255,255,0.05);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .card-ticker {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00d9ff;
        }
        .card-company {
            font-size: 0.9rem;
            color: #94a3b8;
            margin-top: 3px;
        }

        .card-rec {
            padding: 6px 14px;
            border-radius: 15px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .rec-buy { background: #166534; color: #86efac; }
        .rec-hold { background: #854d0e; color: #fde047; }
        .rec-sell { background: #991b1b; color: #fca5a5; }

        .card-prices {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        .card-price {
            text-align: center;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        .card-price-label {
            font-size: 0.75rem;
            color: #64748b;
            text-transform: uppercase;
        }
        .card-price-value {
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 3px;
        }
        .price-current { color: #e0e0e0; }
        .price-target { color: #00d9ff; }
        .price-upside { color: #22c55e; }
        .price-downside { color: #ef4444; }

        .card-sector {
            margin-top: 15px;
            font-size: 0.8rem;
            color: #64748b;
        }

        .footer {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }

        @media (max-width: 768px) {
            .main-title { font-size: 1.8rem; }
            .equity-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="main-title">Equity Research Portfolio</h1>
            <p class="subtitle">Multi-AI Debate Analysis System | 14 Equities</p>
            <div class="ai-badges">
                <span class="ai-badge">Claude Opus 4.5</span>
                <span class="ai-badge">GPT-4</span>
                <span class="ai-badge">Gemini</span>
                <span class="ai-badge">Grok</span>
                <span class="ai-badge">Qwen</span>
            </div>
        </div>

        <div class="equity-grid">
'''

    for eq in all_equities:
        ticker = eq.get('ticker', 'Unknown')
        company = eq.get('company', 'Unknown')
        recommendation = eq.get('recommendation', 'HOLD')
        current_price = eq.get('current_price', 0)
        target_price = eq.get('target_price', 0)
        sector = eq.get('sector', '')
        filename = eq.get('filename', '')

        # Calculate upside/downside
        if current_price and target_price:
            upside = ((target_price - current_price) / current_price) * 100
            upside_class = 'price-upside' if upside >= 0 else 'price-downside'
            upside_str = f"+{upside:.1f}%" if upside >= 0 else f"{upside:.1f}%"
        else:
            upside_class = 'price-current'
            upside_str = 'N/A'

        # Recommendation class
        rec_upper = str(recommendation).upper()
        if 'BUY' in rec_upper:
            rec_class = 'rec-buy'
        elif 'SELL' in rec_upper:
            rec_class = 'rec-sell'
        else:
            rec_class = 'rec-hold'

        html += f'''
            <a href="{filename}" class="equity-card">
                <div class="card-header">
                    <div>
                        <div class="card-ticker">{ticker}</div>
                        <div class="card-company">{company}</div>
                    </div>
                    <span class="card-rec {rec_class}">{recommendation}</span>
                </div>
                <div class="card-prices">
                    <div class="card-price">
                        <div class="card-price-label">Current</div>
                        <div class="card-price-value price-current">${current_price:.2f}</div>
                    </div>
                    <div class="card-price">
                        <div class="card-price-label">Target</div>
                        <div class="card-price-value price-target">${target_price:.2f}</div>
                    </div>
                    <div class="card-price">
                        <div class="card-price-label">Upside</div>
                        <div class="card-price-value {upside_class}">{upside_str}</div>
                    </div>
                </div>
                <div class="card-sector">{sector}</div>
            </a>
'''

    html += '''
        </div>

        <div class="footer">
            <p>Generated by Equity Research Multi-Agent System</p>
            <p>Bull vs Bear vs Critic Multi-AI Debate</p>
            <p>''' + datetime.now().strftime('%Y-%m-%d %H:%M') + '''</p>
        </div>
    </div>
</body>
</html>'''

    return html


def main():
    """Generate all HTML reports"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    context_dir = os.path.join(base_dir, "context")
    debates_dir = os.path.join(context_dir, "debates")
    reports_dir = os.path.join(base_dir, "reports")

    os.makedirs(reports_dir, exist_ok=True)

    all_equities = []

    # Find all debate files
    debate_files = [f for f in os.listdir(debates_dir) if f.startswith('debate_') and f.endswith('.json')]

    print(f"Found {len(debate_files)} debate files")

    for debate_file in debate_files:
        debate_path = os.path.join(debates_dir, debate_file)

        # Find corresponding research file
        research_filename = debate_file.replace('debate_', '')
        research_path = os.path.join(context_dir, research_filename)

        try:
            debate_data = load_json(debate_path)

            # Load research data if exists
            if os.path.exists(research_path):
                research_data = load_json(research_path)
            else:
                research_data = {}

            # Generate individual HTML
            html = generate_equity_html(debate_data, research_data)

            # Save HTML
            html_filename = research_filename.replace('.json', '.html')
            html_path = os.path.join(reports_dir, html_filename)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"Generated: {html_filename}")

            # Collect for index
            ticker = debate_data.get('ticker', research_data.get('ticker', 'Unknown'))
            company = debate_data.get('company', research_data.get('company', 'Unknown'))

            recommendation = debate_data.get('recommendation', debate_data.get('final_recommendation', {}).get('rating', 'HOLD'))
            if isinstance(recommendation, dict):
                recommendation = recommendation.get('rating', 'HOLD')

            current_price = debate_data.get('current_price_hkd', debate_data.get('current_price', research_data.get('current_price', 0)))
            target_price = debate_data.get('probability_weighted_price',
                          debate_data.get('final_recommendation', {}).get('probability_weighted_price', 0))

            sector = debate_data.get('sector', research_data.get('sector', ''))

            all_equities.append({
                'ticker': ticker,
                'company': company,
                'recommendation': recommendation,
                'current_price': current_price,
                'target_price': target_price,
                'sector': sector,
                'filename': html_filename
            })

        except Exception as e:
            print(f"Error processing {debate_file}: {e}")
            import traceback
            traceback.print_exc()

    # Generate index
    index_html = generate_index_html(all_equities)
    index_path = os.path.join(reports_dir, 'index.html')

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)

    print(f"\nGenerated index.html with {len(all_equities)} equities")
    print(f"Reports saved to: {reports_dir}")


if __name__ == "__main__":
    main()
