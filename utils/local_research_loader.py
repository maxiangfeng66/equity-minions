"""
Local Research Data Loader
Loads proprietary equity research from local file system
Enhanced to extract content from PDFs and Excel models for use in DCF cross-referencing
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import re


@dataclass
class ExcelModelData:
    """Financial model data extracted from Excel files"""
    filename: str
    analyst: Optional[str] = None
    firm: Optional[str] = None
    rating: Optional[str] = None
    target_price: Optional[float] = None
    current_price: Optional[float] = None
    upside: Optional[float] = None
    currency: str = "USD"
    wacc: Optional[float] = None
    terminal_growth: Optional[float] = None
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    revenue_projections: Optional[Dict[str, float]] = None  # {year: revenue}
    ebit_projections: Optional[Dict[str, float]] = None  # {year: ebit}
    dcf_value: Optional[float] = None
    publication_date: Optional[str] = None
    key_assumptions: Optional[Dict[str, Any]] = None


@dataclass
class ResearchDocument:
    """A research document from local storage"""
    filename: str
    filepath: str
    doc_type: str  # 'pdf', 'txt', 'xlsx', etc.
    language: str  # 'en', 'zh', etc.
    source: str  # 'broker', 'internal', 'due_diligence', etc.
    summary: Optional[str] = None
    content: Optional[str] = None  # Extracted text content
    financial_data: Optional[Dict] = None  # Extracted financial metrics


@dataclass
class LocalResearchContext:
    """Research context loaded from local files"""
    ticker: str
    company_name: str
    documents: List[ResearchDocument]
    excel_models: List[ExcelModelData] = None  # Extracted Excel model data
    due_diligence_notes: Optional[str] = None
    key_questions: List[str] = None


class LocalResearchLoader:
    """Loads equity research from local file system"""

    # Base path for research files
    BASE_PATH = Path("E:/其他计算机/My Computer/平衡表/平衡表/Equities")

    # Ticker to folder name mapping
    TICKER_FOLDERS = {
        "6682 HK": "6682 第四范式",
        "6682.HK": "6682 第四范式",
        "9660 HK": "9660地平线",
        "9660.HK": "9660地平线",
        "LEGN US": "LEGN 传奇生物",
        "LEGN": "LEGN 传奇生物",
        "20 HK": "20HK SENSETIME",
        "2228 HK": "2228 晶泰",
        "9969 HK": "9969 诺诚建华",
    }

    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = self.BASE_PATH

    def get_folder_for_ticker(self, ticker: str) -> Optional[Path]:
        """Get the research folder path for a ticker"""
        # Normalize ticker: replace dots and underscores with spaces
        ticker_clean = ticker.upper().replace(".", " ").replace("_", " ").strip()

        # Try direct mapping
        if ticker_clean in self.TICKER_FOLDERS:
            folder_name = self.TICKER_FOLDERS[ticker_clean]
            folder_path = self.base_path / folder_name
            if folder_path.exists():
                return folder_path

        # Try partial match
        ticker_num = ticker_clean.split()[0] if " " in ticker_clean else ticker_clean
        for folder in self.base_path.iterdir():
            if folder.is_dir() and ticker_num in folder.name:
                return folder

        return None

    def load_research(self, ticker: str, extract_excel: bool = True) -> Optional[LocalResearchContext]:
        """Load all available research for a ticker"""
        folder = self.get_folder_for_ticker(ticker)
        if not folder:
            return None

        documents = []
        excel_models = []
        due_diligence = None

        # Scan folder for documents
        for item in folder.rglob("*"):
            if item.is_file():
                doc_type = item.suffix.lower().lstrip(".")
                if doc_type in ["pdf", "txt", "xlsx", "docx", "md"]:
                    # Determine language from filename
                    is_chinese = any(ord(c) > 127 for c in item.name)
                    language = "zh" if is_chinese else "en"

                    # Determine source type
                    if "due" in item.name.lower() or "diligence" in item.name.lower():
                        source = "due_diligence"
                        if doc_type == "txt":
                            due_diligence = item.read_text(encoding="utf-8")
                    elif any(broker in item.name for broker in
                            ["华安", "海通", "交银", "申万", "长江", "招商", "麦高"]):
                        source = "broker_chinese"
                    elif "AI report" in str(item.parent) or "report" in item.name.lower():
                        source = "ai_report"
                    else:
                        source = "research"

                    documents.append(ResearchDocument(
                        filename=item.name,
                        filepath=str(item),
                        doc_type=doc_type,
                        language=language,
                        source=source
                    ))

                    # Extract Excel model data
                    if extract_excel and doc_type == "xlsx":
                        model_data = self.extract_excel_model(str(item))
                        if model_data:
                            excel_models.append(model_data)

        # Extract company name from folder
        company_name = folder.name.split(" ", 1)[-1] if " " in folder.name else folder.name

        return LocalResearchContext(
            ticker=ticker,
            company_name=company_name,
            documents=documents,
            excel_models=excel_models if excel_models else None,
            due_diligence_notes=due_diligence,
            key_questions=self._extract_key_questions(due_diligence) if due_diligence else None
        )

    def _extract_key_questions(self, due_diligence: str) -> List[str]:
        """Extract key questions from due diligence notes"""
        questions = []
        lines = due_diligence.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() and ")" in line[:3]):
                # Numbered question like "1) how strong..."
                questions.append(line)
        return questions

    def extract_excel_model(self, filepath: str) -> Optional[ExcelModelData]:
        """Extract financial model data from Excel file"""
        try:
            import pandas as pd

            xl = pd.ExcelFile(filepath)
            sheet_names = [s.lower() for s in xl.sheet_names]

            model_data = ExcelModelData(filename=Path(filepath).name)

            # Try to find key data from various sheets
            # First check for Cover/Metrics sheet with summary data
            for sheet_name in xl.sheet_names:
                if sheet_name.lower() in ['cover', 'metrics', 'summary', 'tear sheet']:
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
                    self._extract_model_summary(df, model_data)
                    break

            # Check for DCF sheet
            for sheet_name in xl.sheet_names:
                if 'dcf' in sheet_name.lower():
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
                    self._extract_dcf_data(df, model_data)
                    break

            # Check for Income Statement/Model sheet for projections
            for sheet_name in xl.sheet_names:
                if any(x in sheet_name.lower() for x in ['income', 'model', 'p&l']):
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
                    self._extract_projections(df, model_data)
                    break

            return model_data if model_data.target_price or model_data.dcf_value else None

        except ImportError:
            print(f"pandas not installed - cannot extract Excel models")
            return None
        except Exception as e:
            print(f"Excel extraction error for {filepath}: {e}")
            return None

    def _extract_model_summary(self, df, model_data: ExcelModelData):
        """Extract summary data from Cover/Metrics sheet"""
        try:
            # Convert to string for regex searching
            text = df.to_string()

            # Extract analyst info
            analyst_patterns = [
                r'([A-Za-z]+\s+[A-Za-z]+),?\s*[\w.]+@[\w.]+',
                r'Primary Analyst[:\s]*([A-Za-z\s,]+)',
            ]
            for pattern in analyst_patterns:
                match = re.search(pattern, text)
                if match:
                    model_data.analyst = match.group(1).strip()
                    break

            # Check for Goldman Sachs or other firms
            if 'gs.com' in text.lower() or 'goldman' in text.lower():
                model_data.firm = "Goldman Sachs"
            elif 'morgan stanley' in text.lower():
                model_data.firm = "Morgan Stanley"
            elif 'jpmorgan' in text.lower() or 'jpm' in text.lower():
                model_data.firm = "JPMorgan"

            # Extract price and target
            price_match = re.search(r'Price[:\s]*\$?([\d.]+)', text, re.IGNORECASE)
            if price_match:
                model_data.current_price = float(price_match.group(1))

            target_match = re.search(r'(?:12m\s*)?(?:Price\s*)?Target[:\s]*\$?([\d.]+)', text, re.IGNORECASE)
            if target_match:
                model_data.target_price = float(target_match.group(1))

            # Extract upside
            upside_match = re.search(r'Upside[:\s]*([\d.]+)%', text, re.IGNORECASE)
            if upside_match:
                model_data.upside = float(upside_match.group(1))

            # Extract rating
            if re.search(r'\bBuy\b', text, re.IGNORECASE):
                model_data.rating = "BUY"
            elif re.search(r'\bHold\b|\bNeutral\b', text, re.IGNORECASE):
                model_data.rating = "HOLD"
            elif re.search(r'\bSell\b', text, re.IGNORECASE):
                model_data.rating = "SELL"

            # Extract market cap
            mcap_match = re.search(r'Market\s*[Cc]ap[:\s]*\$?([\d.]+)\s*(bn|mn|billion|million)', text, re.IGNORECASE)
            if mcap_match:
                value = float(mcap_match.group(1))
                unit = mcap_match.group(2).lower()
                if 'bn' in unit or 'billion' in unit:
                    value *= 1000  # Convert to millions
                if not model_data.key_assumptions:
                    model_data.key_assumptions = {}
                model_data.key_assumptions['market_cap_mn'] = value

        except Exception as e:
            print(f"Error extracting model summary: {e}")

    def _extract_dcf_data(self, df, model_data: ExcelModelData):
        """Extract DCF valuation data from DCF sheet"""
        try:
            text = df.to_string()

            # Extract WACC/discount rate
            wacc_match = re.search(r'(?:WACC|Discount\s*(?:Rate|factor))[:\s@]*\s*([\d.]+)%?', text, re.IGNORECASE)
            if wacc_match:
                value = float(wacc_match.group(1))
                model_data.wacc = value if value < 1 else value / 100  # Handle both 0.09 and 9%

            # Also try to find from "Discount factor @ X%"
            if not model_data.wacc:
                wacc_match2 = re.search(r'Discount\s*factor\s*@\s*([\d.]+)%', text, re.IGNORECASE)
                if wacc_match2:
                    model_data.wacc = float(wacc_match2.group(1)) / 100

            # Extract terminal growth
            tg_match = re.search(r'Terminal\s*(?:Growth|Value)[:\s]*([\d.]+)%?', text, re.IGNORECASE)
            if tg_match:
                value = float(tg_match.group(1))
                model_data.terminal_growth = value if value < 1 else value / 100

            # Extract Enterprise Value
            ev_match = re.search(r'Enterprise\s*Value[:\s]*(?:US)?\$?\s*([\d.,]+)\s*(?:mn|million)?', text, re.IGNORECASE)
            if ev_match:
                model_data.enterprise_value = float(ev_match.group(1).replace(',', ''))

            # Extract Equity Value
            eq_match = re.search(r'Equity\s*Value[:\s]*(?:US)?\$?\s*([\d.,]+)\s*(?:mn|million)?', text, re.IGNORECASE)
            if eq_match:
                model_data.equity_value = float(eq_match.group(1).replace(',', ''))

            # Extract target price from DCF
            tp_match = re.search(r'TP\s*\(US\$\)[:\s]*([\d.]+)', text, re.IGNORECASE)
            if tp_match:
                dcf_target = float(tp_match.group(1))
                model_data.dcf_value = dcf_target
                if not model_data.target_price:
                    model_data.target_price = dcf_target

        except Exception as e:
            print(f"Error extracting DCF data: {e}")

    def _extract_projections(self, df, model_data: ExcelModelData):
        """Extract revenue and EBIT projections from model sheet"""
        try:
            # Look for rows with Revenue and EBIT
            revenue_projections = {}
            ebit_projections = {}

            for idx, row in df.iterrows():
                row_str = str(row.values)

                # Check for revenue row
                if 'revenue' in row_str.lower() and 'total' not in row_str.lower()[:30]:
                    # Extract year columns (looking for years like 2024E, 2025E, etc.)
                    for col_idx, val in enumerate(row.values):
                        try:
                            if isinstance(val, (int, float)) and val > 0:
                                # Try to find the year from header
                                if col_idx < len(df.columns):
                                    for search_row in range(min(20, len(df))):
                                        header_val = str(df.iloc[search_row, col_idx])
                                        year_match = re.search(r'(20\d{2})', header_val)
                                        if year_match:
                                            year = year_match.group(1)
                                            if 'E' in header_val or int(year) >= 2024:
                                                revenue_projections[year] = float(val)
                                            break
                        except:
                            continue
                    if revenue_projections:
                        break

                # Check for EBIT row
                if 'ebit' in row_str.lower() and 'ebitda' not in row_str.lower():
                    for col_idx, val in enumerate(row.values):
                        try:
                            if isinstance(val, (int, float)):
                                for search_row in range(min(20, len(df))):
                                    header_val = str(df.iloc[search_row, col_idx])
                                    year_match = re.search(r'(20\d{2})', header_val)
                                    if year_match:
                                        year = year_match.group(1)
                                        if 'E' in header_val or int(year) >= 2024:
                                            ebit_projections[year] = float(val)
                                        break
                        except:
                            continue

            if revenue_projections:
                model_data.revenue_projections = revenue_projections
            if ebit_projections:
                model_data.ebit_projections = ebit_projections

        except Exception as e:
            print(f"Error extracting projections: {e}")

    def extract_pdf_content(self, filepath: str, max_pages: int = 5) -> Optional[str]:
        """Extract text content from PDF file"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += page.get_text()
            doc.close()
            return text[:10000] if text else None  # Limit to 10k chars
        except ImportError:
            # Try pdfplumber as fallback
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(filepath) as pdf:
                    for page_num in range(min(max_pages, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        text += page.extract_text() or ""
                return text[:10000] if text else None
            except:
                return None
        except Exception as e:
            print(f"PDF extraction error for {filepath}: {e}")
            return None

    def extract_financial_metrics(self, text: str) -> Dict:
        """Extract key financial metrics from text"""
        metrics = {}

        # Price targets (e.g., "target price $52", "目标价 52美元")
        price_patterns = [
            r'target\s*price[:\s]*\$?([\d.]+)',
            r'price\s*target[:\s]*\$?([\d.]+)',
            r'目标价[:\s]*([\d.]+)',
            r'PT[:\s]*\$?([\d.]+)',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).strip()
                    # Skip invalid values like just '.' or empty
                    if value_str and value_str != '.' and re.match(r'^\d+\.?\d*$', value_str):
                        metrics['target_price'] = float(value_str)
                        break
                except (ValueError, AttributeError):
                    continue

        # Revenue/sales figures
        revenue_patterns = [
            r'revenue[:\s]*\$?([\d.,]+)\s*(million|billion|M|B)',
            r'销售额[:\s]*([\d.,]+)\s*(亿|百万)',
            r'营收[:\s]*([\d.,]+)\s*(亿|百万)',
        ]
        for pattern in revenue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(',', ''))
                unit = match.group(2).lower()
                if unit in ['billion', 'b', '亿']:
                    value *= 1000  # Convert to millions
                metrics['revenue_estimate'] = value
                break

        # EPS estimates
        eps_patterns = [
            r'EPS[:\s]*\$?([\-\d.]+)',
            r'每股收益[:\s]*([\-\d.]+)',
        ]
        for pattern in eps_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics['eps_estimate'] = float(match.group(1))
                break

        # Ratings
        if any(word in text.lower() for word in ['buy', '买入', 'outperform']):
            metrics['rating'] = 'BUY'
        elif any(word in text.lower() for word in ['hold', '持有', 'neutral']):
            metrics['rating'] = 'HOLD'
        elif any(word in text.lower() for word in ['sell', '卖出', 'underperform']):
            metrics['rating'] = 'SELL'

        return metrics if metrics else None

    def load_research_with_content(self, ticker: str, extract_content: bool = True) -> Optional[LocalResearchContext]:
        """Load research with extracted PDF content for DCF cross-referencing"""
        context = self.load_research(ticker)
        if not context:
            return None

        if extract_content:
            for doc in context.documents:
                if doc.doc_type == 'pdf':
                    content = self.extract_pdf_content(doc.filepath)
                    if content:
                        doc.content = content
                        doc.financial_data = self.extract_financial_metrics(content)

        return context

    def get_financial_consensus(self, ticker: str) -> Dict:
        """Get consensus financial data from all broker reports"""
        context = self.load_research_with_content(ticker)
        if not context:
            return {}

        target_prices = []
        ratings = {'BUY': 0, 'HOLD': 0, 'SELL': 0}

        for doc in context.documents:
            if doc.financial_data:
                if 'target_price' in doc.financial_data:
                    target_prices.append(doc.financial_data['target_price'])
                if 'rating' in doc.financial_data:
                    ratings[doc.financial_data['rating']] += 1

        consensus = {}
        if target_prices:
            consensus['avg_target_price'] = sum(target_prices) / len(target_prices)
            consensus['min_target_price'] = min(target_prices)
            consensus['max_target_price'] = max(target_prices)
            consensus['target_price_sources'] = len(target_prices)

        consensus['ratings'] = ratings
        consensus['consensus_rating'] = max(ratings, key=ratings.get) if any(ratings.values()) else None

        return consensus

    def get_research_summary(self, ticker: str, include_financial_consensus: bool = True) -> str:
        """Get a text summary of available research for injection into prompts"""
        context = self.load_research(ticker)
        if not context:
            return f"No local research found for {ticker}"

        lines = [
            f"LOCAL RESEARCH CONTEXT FOR {ticker}",
            "=" * 50,
            f"Company: {context.company_name}",
            f"Documents Available: {len(context.documents)}",
            ""
        ]

        # Group by source
        by_source = {}
        for doc in context.documents:
            if doc.source not in by_source:
                by_source[doc.source] = []
            by_source[doc.source].append(doc)

        lines.append("Key Research Files:")
        for source, docs in by_source.items():
            for doc in docs:
                lines.append(f"- {doc.filename} ({doc.source})")

        # Add Excel model data if available
        if context.excel_models:
            lines.append("\n" + "=" * 50)
            lines.append("PROPRIETARY FINANCIAL MODELS (from Excel):")
            lines.append("-" * 30)
            for model in context.excel_models:
                lines.append(f"\n  Model: {model.filename}")
                if model.firm:
                    lines.append(f"  Source: {model.firm}")
                if model.analyst:
                    lines.append(f"  Analyst: {model.analyst}")
                if model.rating:
                    lines.append(f"  Rating: {model.rating}")
                if model.target_price:
                    lines.append(f"  Target Price: ${model.target_price:.2f}")
                if model.current_price:
                    lines.append(f"  Reference Price: ${model.current_price:.2f}")
                if model.upside:
                    lines.append(f"  Upside: {model.upside:.1f}%")
                if model.wacc:
                    lines.append(f"  WACC: {model.wacc*100:.1f}%")
                if model.terminal_growth:
                    lines.append(f"  Terminal Growth: {model.terminal_growth*100:.1f}%")
                if model.enterprise_value:
                    lines.append(f"  Enterprise Value: ${model.enterprise_value:,.0f}mn")
                if model.dcf_value:
                    lines.append(f"  DCF-Implied Price: ${model.dcf_value:.2f}")
                if model.revenue_projections:
                    lines.append(f"  Revenue Projections:")
                    for year, rev in sorted(model.revenue_projections.items()):
                        lines.append(f"    {year}: ${rev:,.1f}mn")
                if model.ebit_projections:
                    lines.append(f"  EBIT Projections:")
                    for year, ebit in sorted(model.ebit_projections.items()):
                        lines.append(f"    {year}: ${ebit:,.1f}mn")

            lines.append("\n  *** CRITICAL: Use Excel model assumptions as reference for your DCF ***")
            lines.append("  *** Cross-validate your WACC, growth rates, and terminal value ***")

        # Add financial consensus if available
        if include_financial_consensus:
            consensus = self.get_financial_consensus(ticker)
            if consensus:
                lines.append("\n" + "=" * 50)
                lines.append("BROKER CONSENSUS DATA (from proprietary research):")
                lines.append("-" * 30)
                if 'avg_target_price' in consensus:
                    lines.append(f"  Average Target Price: ${consensus['avg_target_price']:.2f}")
                    lines.append(f"  Target Range: ${consensus['min_target_price']:.2f} - ${consensus['max_target_price']:.2f}")
                    lines.append(f"  Sources: {consensus['target_price_sources']} broker reports")
                if consensus.get('consensus_rating'):
                    lines.append(f"  Consensus Rating: {consensus['consensus_rating']}")
                    ratings = consensus.get('ratings', {})
                    lines.append(f"  Rating Breakdown: BUY={ratings.get('BUY',0)}, HOLD={ratings.get('HOLD',0)}, SELL={ratings.get('SELL',0)}")
                lines.append("")
                lines.append("IMPORTANT: Cross-reference your DCF target with broker consensus above!")
                lines.append("If your target differs >30% from broker consensus, explain why.")

        if context.due_diligence_notes:
            lines.append("\nDUE DILIGENCE NOTES:")
            lines.append("-" * 30)
            lines.append(context.due_diligence_notes)

        return "\n".join(lines)


def get_local_research_context(ticker: str) -> str:
    """
    Convenience function to get research context for a ticker
    Returns formatted string for prompt injection
    """
    loader = LocalResearchLoader()
    return loader.get_research_summary(ticker)


def get_excel_model_data(ticker: str) -> Optional[Dict]:
    """
    Get Excel model data for a ticker as a dictionary
    Returns the most complete model data found
    """
    loader = LocalResearchLoader()
    context = loader.load_research(ticker)
    if not context or not context.excel_models:
        return None

    # Find the model with most data
    best_model = None
    best_score = 0

    for model in context.excel_models:
        score = 0
        if model.target_price:
            score += 3
        if model.wacc:
            score += 2
        if model.dcf_value:
            score += 2
        if model.revenue_projections:
            score += len(model.revenue_projections)
        if model.ebit_projections:
            score += len(model.ebit_projections)
        if model.firm:
            score += 1
        if model.analyst:
            score += 1

        if score > best_score:
            best_score = score
            best_model = model

    if not best_model:
        return None

    return {
        "filename": best_model.filename,
        "firm": best_model.firm,
        "analyst": best_model.analyst,
        "rating": best_model.rating,
        "target_price": best_model.target_price,
        "current_price": best_model.current_price,
        "upside": best_model.upside,
        "wacc": best_model.wacc,
        "terminal_growth": best_model.terminal_growth,
        "enterprise_value": best_model.enterprise_value,
        "equity_value": best_model.equity_value,
        "dcf_value": best_model.dcf_value,
        "revenue_projections": best_model.revenue_projections,
        "ebit_projections": best_model.ebit_projections,
    }


if __name__ == "__main__":
    # Test the loader
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "6682 HK"
    print(get_local_research_context(ticker))
