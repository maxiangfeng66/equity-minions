# Configuration file for API keys and settings
# Fill in your API keys below

API_KEYS = {
    "openai": "",  # GPT API key - get from https://platform.openai.com/api-keys
    "google": "",  # Gemini API key - get from https://aistudio.google.com/apikey
    "xai": "",     # Grok API key - get from https://console.x.ai/
    "deepseek": "",  # DeepSeek API key - get from https://platform.deepseek.com/
    "dashscope": "",  # Qwen (Alibaba) AccessKey ID - get from Alibaba Cloud console
    "dashscope_secret": "",  # Qwen AccessKey Secret
}

# Equity list with Bloomberg tickers and company info (CORRECTED from list.txt)
EQUITIES = {
    "6682 HK": {"name": "Beijing Fourth Paradigm Technology", "sector": "Technology", "industry": "AI/Machine Learning"},
    "LEGN US": {"name": "Legend Biotech", "sector": "Healthcare", "industry": "Biotechnology"},
    "9660 HK": {"name": "Horizon Robotics", "sector": "Technology", "industry": "Autonomous Driving/AI"},
    "9926 HK": {"name": "Akeso Inc", "sector": "Healthcare", "industry": "Biotechnology"},
    "762 HK": {"name": "China Unicom Hong Kong", "sector": "Communication Services", "industry": "Telecom"},
    "1799 HK": {"name": "Xinte Energy", "sector": "Utilities", "industry": "Wind/Solar Energy"},
    "3888 HK": {"name": "Kingsoft Corp", "sector": "Technology", "industry": "Software"},
    "3800 HK": {"name": "GCL Technology Holdings", "sector": "Technology", "industry": "Solar/Polysilicon"},
    "1045 HK": {"name": "APT Satellite Holdings", "sector": "Communication Services", "industry": "Satellite"},
    "2696 HK": {"name": "Shanghai Henlius Biotech", "sector": "Healthcare", "industry": "Biotechnology/Biosimilars"},
    "9969 HK": {"name": "InnoCare Pharma", "sector": "Healthcare", "industry": "Biotechnology/Oncology"},
    "3319 HK": {"name": "A-Living Smart City Services", "sector": "Real Estate", "industry": "Property Management"},
    "2869 HK": {"name": "Greentown Service Group", "sector": "Real Estate", "industry": "Property Management"},
    "1816 HK": {"name": "CGN Power Co", "sector": "Utilities", "industry": "Nuclear Power"},
}

# Analysis parameters
DISCOUNT_RATES = [0.08, 0.09, 0.10, 0.11]  # 8%, 9%, 10%, 11%
SCENARIOS = ["super_bear", "bear", "base", "bull", "super_bull"]
SCENARIO_PROBABILITIES = {
    "super_bear": 0.05,
    "bear": 0.20,
    "base": 0.50,
    "bull": 0.20,
    "super_bull": 0.05
}

# Number of debate rounds for multi-agent system
DEBATE_ROUNDS = 10

# Output directory
OUTPUT_DIR = "reports"
