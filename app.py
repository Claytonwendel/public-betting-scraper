import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def scrape_mlb_data():
    """Scrape MLB betting data using the tbody structure"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        logger.info(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        games = []
        
        # Find all tbody elements with class "text-base-300"
        game_bodies = soup.find_all('tbody', class_='text-base-300')
        logger.info(f"Found {len(game_bodies)} game tbody elements")
        
        for tbody in game_bodies:
            try:
                # Get all tr rows in this tbody
                rows = tbody.find_all('tr')
                
                if len(rows) < 3:  # Need at least 3 rows (time, away team, home team)
                    continue
                
                # First row contains the date/time
                time_row = rows[0]
                time_text = time_row.get_text(strip=True)
                # Extract time pattern like "Jun 25, 9:45 PM"
                time_match = re.search(r'(\w+ \d+, \d+:\d+ [AP]M)', time_text)
                game_time = time_match.group(1) if time_match else time_text
                
                # Second row is away team
                away_row = rows[1]
                away_cells = away_row.find_all('td')
                
                # Third row is home team
                home_row = rows[2]
                home_cells = home_row.find_all('td')
                
                # Extract team abbreviations
                # Team name is usually in the first cell or has an image with the team
                away_team_cell = away_row.find(['td', 'th'])
                home_team_cell = home_row.find(['td', 'th'])
                
                # Extract team text - look for uppercase abbreviations
                away_text = away_team_cell.get_text(strip=True) if away_team_cell else ""
                home_text = home_team_cell.get_text(strip=True) if home_team_cell else ""
                
                # Find team abbreviations (2-4 letter uppercase)
                away_match = re.search(r'\b([A-Z]{2,4})\b', away_text)
                home_match = re.search(r'\b([A-Z]{2,4})\b', home_text)
                
                away_team = away_match.group(1) if away_match else away_text[:3].upper()
                home_team = home_match.group(1) if home_match else home_text[:3].upper()
                
                # Extract all percentages from the rows
                away_percentages = re.findall(r'(\d+)%', away_row.get_text())
                home_percentages = re.findall(r'(\d+)%', home_row.get_text())
                
                # Create game data
                # Based on the structure: Moneyline (BET%, $%), Spread (BET%, $%), Total (BET%, $%)
                game_data = {
                    'game_time': game_time,
                    'away_team': away_team,
                    'home_team': home_team,
                    # Away team percentages
                    'away_moneyline_bets_pct': away_percentages[0] + '%' if len(away_percentages) > 0 else 'N/A',
                    'away_moneyline_money_pct': away_percentages[1] + '%' if len(away_percentages) > 1 else 'N/A',
                    'away_spread_bets_pct': away_percentages[2] + '%' if len(away_percentages) > 2 else 'N/A',
                    'away_spread_money_pct': away_percentages[3] + '%' if len(away_percentages) > 3 else 'N/A',
                    'away_total_bets_pct': away_percentages[4] + '%' if len(away_percentages) > 4 else 'N/A',
                    'away_total_money_pct': away_percentages[5] + '%' if len(away_percentages) > 5 else 'N/A',
                    # Home team percentages
                    'home_moneyline_bets_pct': home_percentages[0] + '%' if len(home_percentages) > 0 else 'N/A',
                    'home_moneyline_money_pct': home_percentages[1] + '%' if len(home_percentages) > 1 else 'N/A',
                    'home_spread_bets_pct': home_percentages[2] + '%' if len(home_percentages) > 2 else 'N/A',
                    'home_spread_money_pct': home_percentages[3] + '%' if len(home_percentages) > 3 else 'N/A',
                    'home_total_bets_pct': home_percentages[4] + '%' if len(home_percentages) > 4 else 'N/A',
                    'home_total_money_pct': home_percentages[5] + '%' if len(home_percentages) > 5 else 'N/A',
                    # For backwards compatibility, also include simplified fields
                    'moneyline_bets_pct': away_percentages[0] + '%' if len(away_percentages) > 0 else 'N/A',
                    'moneyline_money_pct': away_percentages[1] + '%' if len(away_percentages) > 1 else 'N/A',
                    'spread_bets_pct': away_percentages[2] + '%' if len(away_percentages) > 2 else 'N/A',
                    'spread_money_pct': away_percentages[3] + '%' if len(away_percentages) > 3 else 'N/A',
                    'total_bets_pct': away_percentages[4] + '%' if len(away_percentages) > 4 else 'N/A',
                    'total_money_pct': away_percentages[5] + '%' if len(away_percentages) > 5 else 'N/A',
                    'timestamp': datetime.now().isoformat()
                }
                
                games.append(game_data)
                logger.info(f"Successfully parsed game: {away_team} @ {home_team} at {game_time}")
                
            except Exception as e:
                logger.error(f"Error parsing game tbody: {str(e)}")
                continue
        
        logger.info(f"Total games parsed: {len(games)}")
        return games
        
    except Exception as e:
        logger.error(f"Error scraping MLB data: {str(e)}")
        return []

@app.route('/')
def home():
    return jsonify({
        "message": "Public Betting Scraper API",
        "endpoints": {
            "/api/health": "Health check",
            "/api/betting/mlb": "Get MLB betting data",
            "/api/debug": "Debug information"
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/betting/mlb')
def get_mlb_data():
    data = scrape_mlb_data()
    
    return jsonify({
        "sport": "mlb",
        "data": data,
        "count": len(data),
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/debug')
def debug_info():
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Count tbody elements with class text-base-300
        game_bodies = soup.find_all('tbody', class_='text-base-300')
        
        # Get sample of first tbody structure
        sample_structure = None
        if game_bodies:
            first_tbody = game_bodies[0]
            rows = first_tbody.find_all('tr')
            sample_structure = {
                "row_count": len(rows),
                "rows": []
            }
            for i, row in enumerate(rows[:3]):  # First 3 rows
                cells = row.find_all(['td', 'th'])
                sample_structure["rows"].append({
                    "row": i,
                    "cell_count": len(cells),
                    "text": row.get_text(strip=True)[:100]
                })
        
        return jsonify({
            "status": "OK",
            "tbody_count": len(game_bodies),
            "sample_tbody_structure": sample_structure
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
