"""
StockInsight - Flask Stock Analysis Dashboard
Uses yfinance for data (no API key required)
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = "stockinsight_secret_2024"

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "stock.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                company_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# ─────────────────────────────────────────────
# DATA FETCHING & INDICATORS
# ─────────────────────────────────────────────
def fetch_stock_data(ticker, period="1mo"):
    """Fetch comprehensive stock data using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Validate ticker — try fast_info as fallback for yfinance 1.x
        price = (info.get("currentPrice") or info.get("regularMarketPrice"))
        if not price:
            try:
                fi = stock.fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
            except Exception:
                pass
        if not price:
            return None, "Invalid ticker or data unavailable."

        # Price data
        price = float(price)
        prev_close = (info.get("previousClose") or info.get("regularMarketPreviousClose"))
        if not prev_close:
            try:
                prev_close = getattr(stock.fast_info, "previous_close", None)
            except Exception:
                pass
        prev_close = float(prev_close) if prev_close else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        # Historical data for chart (user selected period)
        hist = stock.history(period=period)
        # Historical data for indicators (always 90 days)
        hist_90 = stock.history(period="90d")

        # Technical Indicators (using 90 days)
        indicators = calculate_indicators(hist_90)

        # Chart data (using selected period) — includes OHLC for candlestick mode
        chart_data = []
        if not hist.empty:
            chart_data = [
                {
                    "date":  str(d.date()),
                    "open":  round(float(o), 2),
                    "high":  round(float(h), 2),
                    "low":   round(float(l), 2),
                    "close": round(float(c), 2),
                }
                for d, o, h, l, c in zip(
                    hist.index, hist["Open"], hist["High"], hist["Low"], hist["Close"]
                )
            ]

        # Financials
        financials = fetch_financials(stock)

        # --- Analyst Ratings Data ---
        analyst_data = {}
        try:
            # Get analyst recommendations summary (e.g., number of Strong Buy, Buy, etc.)
            rec_summary = stock.recommendations_summary
            if rec_summary is not None and not rec_summary.empty:
                # The summary is typically a single row with counts for each rating
                summary_row = rec_summary.iloc[-1]
                analyst_data["summary"] = {
                    "strongBuy": int(summary_row.get('strongBuy', 0)),
                    "buy": int(summary_row.get('buy', 0)),
                    "hold": int(summary_row.get('hold', 0)),
                    "sell": int(summary_row.get('sell', 0)),
                    "strongSell": int(summary_row.get('strongSell', 0)),
                }
                total = sum(analyst_data["summary"].values())
                analyst_data["summary"]["total"] = total

            # Get latest analyst action (upgrade/downgrade)
            recommendations = stock.recommendations
            if recommendations is not None and not recommendations.empty:
                latest = recommendations.iloc[-1]
                analyst_data["latest"] = {
                    "firm": latest.get('Firm', 'N/A'),
                    "action": latest.get('Action', 'N/A'),
                    "to_grade": latest.get('To Grade', 'N/A'),
                    "from_grade": latest.get('From Grade', 'N/A'),
                    "date": str(latest.name.date()) if hasattr(latest.name, 'date') else str(latest.name)[:10]
                }

            # Get price target (if available)
            target_mean = info.get('targetMeanPrice')
            target_high = info.get('targetHighPrice')
            target_low = info.get('targetLowPrice')
            if target_mean:
                analyst_data["target"] = {
                    "mean": round(float(target_mean), 2),
                    "high": round(float(target_high), 2) if target_high else None,
                    "low": round(float(target_low), 2) if target_low else None,
                }

            # Calculate consensus (simple: map numeric average to text)
            if "summary" in analyst_data and analyst_data["summary"]["total"] > 0:
                s = analyst_data["summary"]
                # Weighted score: Strong Buy=1, Buy=2, Hold=3, Sell=4, Strong Sell=5
                weighted = (s["strongBuy"] * 1 + s["buy"] * 2 + s["hold"] * 3 +
                            s["sell"] * 4 + s["strongSell"] * 5)
                avg_score = weighted / s["total"]
                if avg_score <= 1.5:
                    consensus = "Strong Buy"
                elif avg_score <= 2.5:
                    consensus = "Buy"
                elif avg_score <= 3.5:
                    consensus = "Hold"
                elif avg_score <= 4.5:
                    consensus = "Sell"
                else:
                    consensus = "Strong Sell"
                analyst_data["consensus"] = consensus

        except Exception as e:
            print(f"Could not fetch analyst data for {ticker}: {e}")
            analyst_data = {}

        return {
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName", ticker.upper()),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "market_cap": format_large_number(info.get("marketCap")),
            "market_cap_raw": info.get("marketCap"),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": format_large_number(info.get("volume")),
            "avg_volume": format_large_number(info.get("averageVolume")),
            "pe_ratio": round(info.get("trailingPE", 0) or 0, 2),
            "eps": round(info.get("trailingEps", 0) or 0, 2),
            "week_52_high": round(info.get("fiftyTwoWeekHigh", 0) or 0, 2),
            "week_52_low": round(info.get("fiftyTwoWeekLow", 0) or 0, 2),
            "dividend_yield": round((info.get("dividendYield") or 0) * 100, 2),
            "beta": round(info.get("beta") or 0, 2),
            "indicators": indicators,
            "chart_data": chart_data,
            "financials": financials,
            "description": info.get("longBusinessSummary", "")[:400] + "..." if info.get("longBusinessSummary") and len(info.get("longBusinessSummary", "")) > 400 else info.get("longBusinessSummary", ""),
            "analyst": analyst_data,   # <-- new field
        }, None

    except Exception as e:
        return None, str(e)


def calculate_indicators(hist):
    """Calculate MA20, MA50, RSI, and trend signal."""
    if hist.empty or len(hist) < 14:
        return {"ma20": None, "ma50": None, "rsi": None, "trend": "NEUTRAL", "signal": "Insufficient data"}

    close = hist["Close"]

    # Moving Averages
    ma20 = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
    ma50 = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
    current = round(float(close.iloc[-1]), 2)

    # RSI (14-period)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2)

    # Trend determination
    trend = determine_trend(current, ma20, ma50, rsi)

    return {
        "ma20": ma20,
        "ma50": ma50,
        "rsi": rsi,
        "current": current,
        "trend": trend["label"],
        "trend_color": trend["color"],
        "signal": trend["signal"],
    }


def determine_trend(price, ma20, ma50, rsi):
    """Rule-based trend analysis."""
    bullish_signals = 0
    bearish_signals = 0

    if ma20 and price > ma20:
        bullish_signals += 1
    elif ma20:
        bearish_signals += 1

    if ma50 and price > ma50:
        bullish_signals += 1
    elif ma50:
        bearish_signals += 1

    if rsi:
        if rsi < 30:
            return {"label": "OVERSOLD", "color": "warning", "signal": f"RSI at {rsi} — potentially undervalued, watch for reversal."}
        elif rsi > 70:
            return {"label": "OVERBOUGHT", "color": "danger", "signal": f"RSI at {rsi} — overbought conditions, caution advised."}

    if bullish_signals >= 2:
        return {"label": "BULLISH", "color": "success", "signal": "Price above key moving averages. Uptrend momentum confirmed."}
    elif bearish_signals >= 2:
        return {"label": "BEARISH", "color": "danger", "signal": "Price below key moving averages. Downtrend in progress."}
    else:
        return {"label": "NEUTRAL", "color": "warning", "signal": "Mixed signals — no clear directional bias detected."}


def fetch_financials(stock):
    """Fetch quarterly financials — compatible with yfinance 0.2.x and 1.x."""
    try:
        # yfinance 1.x uses quarterly_income_stmt; older versions use quarterly_financials
        df = None
        for attr in ["quarterly_income_stmt", "quarterly_financials"]:
            candidate = getattr(stock, attr, None)
            if candidate is not None and not candidate.empty:
                df = candidate
                break

        if df is None or df.empty:
            return []

        # Normalise: financial items must be in the INDEX, dates in columns.
        # Some yfinance builds return it transposed — detect and flip.
        # Heuristic: if first column label looks like a date, rows are metrics.
        first_col = df.columns[0]
        if not hasattr(first_col, "year"):
            df = df.T  # transpose so dates become columns

        # Map of common label variants across yfinance versions
        REVENUE_KEYS   = ["Total Revenue", "TotalRevenue", "Revenue", "Operating Revenue"]
        NET_INCOME_KEYS = ["Net Income", "NetIncome", "Net Income Common Stockholders",
                           "Net Income Applicable To Common Shares"]

        def _get_row(keys):
            for k in keys:
                if k in df.index:
                    return df.loc[k]
            return None

        rev_row = _get_row(REVENUE_KEYS)
        ni_row  = _get_row(NET_INCOME_KEYS)

        rows = []
        for col in df.columns[:4]:  # last 4 quarters
            revenue    = rev_row[col] if rev_row is not None else None
            net_income = ni_row[col]  if ni_row  is not None else None

            # Clean NaN / None
            def safe(v):
                try:
                    return None if v is None or pd.isna(v) else float(v)
                except Exception:
                    return None

            rev_val = safe(revenue)
            ni_val  = safe(net_income)

            rows.append({
                "quarter": str(col.date()) if hasattr(col, "date") else str(col)[:10],
                "revenue":       format_large_number(rev_val),
                "net_income":    format_large_number(ni_val),
                "net_income_raw": ni_val or 0,
            })

        return rows

    except Exception as e:
        print(f"[financials error] {e}")
        return []


def generate_smart_summary(data):
    """Rule-based smart summary of stock conditions."""
    summaries = []
    ind = data.get("indicators", {})
    rsi = ind.get("rsi")
    trend = ind.get("trend", "NEUTRAL")
    change_pct = data.get("change_pct", 0)
    pe = data.get("pe_ratio", 0)

    # Price movement
    if change_pct > 2:
        summaries.append(f"Strong upward momentum today with a +{change_pct}% gain.")
    elif change_pct < -2:
        summaries.append(f"Significant selling pressure today with a {change_pct}% decline.")
    elif change_pct > 0:
        summaries.append(f"Modest gains of +{change_pct}% in today's session.")
    else:
        summaries.append(f"Slight pullback of {change_pct}% in today's session.")

    # Trend
    if trend == "BULLISH":
        summaries.append("Technical indicators show bullish momentum with price above key moving averages.")
    elif trend == "BEARISH":
        summaries.append("Price action remains below key moving averages, signaling continued weakness.")
    elif trend == "OVERBOUGHT":
        summaries.append("RSI signals overbought territory — a short-term pullback may be imminent.")
    elif trend == "OVERSOLD":
        summaries.append("RSI signals oversold conditions — a relief rally could be on the horizon.")

    # Valuation
    if pe and pe > 0:
        if pe > 40:
            summaries.append(f"High P/E of {pe}x reflects growth premium or elevated investor expectations.")
        elif pe < 15:
            summaries.append(f"Low P/E of {pe}x may indicate undervaluation or slower growth expectations.")

    return " ".join(summaries) if summaries else "Insufficient data to generate a summary."


def format_large_number(n):
    """Format large numbers to readable strings."""
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12:
            return f"${n/1e12:.2f}T"
        elif abs(n) >= 1e9:
            return f"${n/1e9:.2f}B"
        elif abs(n) >= 1e6:
            return f"${n/1e6:.2f}M"
        else:
            return f"${n:,.0f}"
    except Exception:
        return "N/A"


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["GET"])
def search():
    ticker = request.args.get("ticker", "").strip().upper()
    if not ticker:
        flash("Please enter a ticker symbol.", "warning")
        return redirect(url_for("index"))
    return redirect(url_for("stock_detail", ticker=ticker))


@app.route("/stock/<ticker>")
def stock_detail(ticker):
    ticker = ticker.upper().strip()
    period = request.args.get("period", "1mo")
    data, error = fetch_stock_data(ticker, period=period)

    if error or not data:
        return render_template("stock.html", error=error or "Unable to fetch data.", ticker=ticker)

    # Check watchlist status
    with get_db() as conn:
        in_watchlist = conn.execute(
            "SELECT 1 FROM watchlist WHERE ticker = ?", (ticker,)
        ).fetchone() is not None

    summary = generate_smart_summary(data)
    chart_json = json.dumps(data["chart_data"])

    return render_template(
        "stock.html",
        data=data,
        in_watchlist=in_watchlist,
        summary=summary,
        chart_json=chart_json,
        ticker=ticker,
        current_period=period,
    )


@app.route("/watchlist")
def watchlist():
    with get_db() as conn:
        stocks = conn.execute(
            "SELECT * FROM watchlist ORDER BY added_at DESC"
        ).fetchall()

    watchlist_data = []
    for s in stocks:
        try:
            stock = yf.Ticker(s["ticker"])
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev = info.get("previousClose") or price
            change_pct = round(((price - prev) / prev * 100) if prev else 0, 2)
            watchlist_data.append({
                "id": s["id"],
                "ticker": s["ticker"],
                "company_name": s["company_name"] or s["ticker"],
                "price": round(float(price), 2),
                "change_pct": change_pct,
                "added_at": s["added_at"],
            })
        except Exception:
            watchlist_data.append({
                "id": s["id"],
                "ticker": s["ticker"],
                "company_name": s["company_name"] or s["ticker"],
                "price": 0,
                "change_pct": 0,
                "added_at": s["added_at"],
            })

    return render_template("watchlist.html", stocks=watchlist_data)


@app.route("/add", methods=["POST"])
def add_to_watchlist():
    ticker = request.form.get("ticker", "").upper().strip()
    company_name = request.form.get("company_name", "").strip()
    if not ticker:
        flash("Invalid ticker.", "danger")
        return redirect(url_for("index"))
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist (ticker, company_name) VALUES (?, ?)",
                (ticker, company_name),
            )
            conn.commit()
        flash(f"{ticker} added to your watchlist!", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("stock_detail", ticker=ticker))


@app.route("/remove", methods=["POST"])
def remove_from_watchlist():
    ticker = request.form.get("ticker", "").upper().strip()
    redirect_to = request.form.get("redirect", "watchlist")
    if not ticker:
        return redirect(url_for("watchlist"))
    with get_db() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        conn.commit()
    flash(f"{ticker} removed from watchlist.", "info")
    if redirect_to == "stock":
        return redirect(url_for("stock_detail", ticker=ticker))
    return redirect(url_for("watchlist"))


@app.route("/api/suggest")
def suggest():
    """Simple ticker suggestions for auto-complete."""
    POPULAR = [
        {"ticker": "AAPL", "name": "Apple Inc."},
        {"ticker": "MSFT", "name": "Microsoft Corp."},
        {"ticker": "GOOGL", "name": "Alphabet Inc."},
        {"ticker": "AMZN", "name": "Amazon.com Inc."},
        {"ticker": "NVDA", "name": "NVIDIA Corp."},
        {"ticker": "META", "name": "Meta Platforms"},
        {"ticker": "TSLA", "name": "Tesla Inc."},
        {"ticker": "JPM", "name": "JPMorgan Chase"},
        {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
        {"ticker": "V", "name": "Visa Inc."},
        {"ticker": "JNJ", "name": "Johnson & Johnson"},
        {"ticker": "WMT", "name": "Walmart Inc."},
        {"ticker": "XOM", "name": "Exxon Mobil"},
        {"ticker": "NFLX", "name": "Netflix Inc."},
        {"ticker": "AMD", "name": "Advanced Micro Devices"},
    ]
    q = request.args.get("q", "").upper()
    if not q:
        return jsonify([])
    results = [s for s in POPULAR if q in s["ticker"] or q.lower() in s["name"].lower()]
    return jsonify(results[:5])

@app.route("/api/chart_data")
def chart_data():
    """AJAX endpoint: returns OHLC + close price data for a given ticker and period."""
    ticker = request.args.get("ticker", "").upper().strip()
    period = request.args.get("period", "1mo")
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            return jsonify({"error": "No data"}), 404
        data = [
            {
                "date":  str(d.date()),
                "open":  round(float(o), 2),
                "high":  round(float(h), 2),
                "low":   round(float(l), 2),
                "close": round(float(c), 2),
            }
            for d, o, h, l, c in zip(
                hist.index, hist["Open"], hist["High"], hist["Low"], hist["Close"]
            )
        ]
        return jsonify({"chartData": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
