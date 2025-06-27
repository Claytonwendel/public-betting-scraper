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
    """Scrape MLB betting data from tbody with class text-base-300"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        logger.info(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        games = []
        
        # Find ALL tbody elements with class containing "text-base"
        # Using a more flexible approach since class might be dynamic
        all_tbody = soup.find_all('tbody')
        logger.info(f"Found {len(all_tbody)} total tbody elements")
        
        game_tbody_list = []
        
        # Check each tbody to see if it contains betting percentages
        for tbody in all_tbody:
            tbody_text = tbody.get_text()
            # If tbody contains percentages, it's likely a game tbody
            if '%' in tbody_text and 'ML RECORD' not in tbody_text.upper():
                game_tbody_list.append(tbody)
        
        logger.info(f"Found {len(game_tbody_list)} tbody elements with betting data")
        
        # Process each game tbody
        for tbody_idx, tbody in enumerate(game_tbody_list):
            try:
                rows = tbody.find_all('tr')
                logger.info(f"Processing tbody {tbody_idx} with {len(rows)} rows")
                
                # Group rows by game (typically 3 rows: time, away, home)
                i = 0
                while i < len(rows):
                    try:
                        # Check if we have enough rows for a complete game
                        if i + 2 >= len(rows):
                            break
                        
                        # Row 1: Date/Time
                        time_row = rows[i]
                        time_text = time_row.get_text(strip=True)
                        
                        # Extract time - looking for patterns like "Jun 26, 1:10 PM"
                        time_match = re.search(r'([A-Za-z]+ \d+,?\s*\d{1,2}:\d{2}\s*[AP]M)', time_text)
                        if not time_match:
                            # Try just time
                            time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', time_text)
                        
                        # Row 2: Away team
                        away_row = rows[i + 1]
                        away_text = away_row.get_text(strip=True)
                        
                        # Row 3: Home team  
                        home_row = rows[i + 2]
                        home_text = home_row.get_text(strip=True)
                        
                        # Check if these rows contain percentages (betting data)
                        if '%' not in away_text or '%' not in home_text:
                            i += 1
                            continue
                        
                        game_time = time_match.group(1) if time_match else time_text
                        
                        # Extract team names from rows
                        # Look for team abbreviations at the start of the row
                        away_team_match = re.search(r'^([A-Z]{2,4})\b', away_text)
                        home_team_match = re.search(r'^([A-Z]{2,4})\b', home_text)
                        
                        if not away_team_match or not home_team_match:
                            # Try finding any team abbreviation
                            away_teams = re.findall(r'\b([A-Z]{2,4})\b', away_text)
                            home_teams = re.findall(r'\b([A-Z]{2,4})\b', home_text)
                            
                            # Filter out non-team words
                            non_teams = ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'EDT', 'CDT', 'PDT', 'MDT']
                            away_teams = [t for t in away_teams if t not in non_teams]
                            home_teams = [t for t in home_teams if t not in non_teams]
                            
                            away_team = away_teams[0] if away_teams else 'UNK'
                            home_team = home_teams[0] if home_teams else 'UNK'
                        else:
                            away_team = away_team_match.group(1)
                            home_team = home_team_match.group(1)
                        
                        # Extract percentages from each row
                        away_percentages = re.findall(r'(\d+)%', away_text)
                        home_percentages = re.findall(r'(\d+)%', home_text)
                        
                        # Create game data
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
                            # Simplified fields for frontend
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
                        
                        # Move to next game (skip 3 rows)
                        i += 3
                        
                    except Exception as e:
                        logger.error(f"Error parsing game at row {i}: {str(e)}")
                        i += 1
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing tbody {tbody_idx}: {str(e)}")
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
            "/api/debug": "Debug information",
            "/api/debug/tbody": "Debug tbody content",
            "/api/debug/percentages": "Debug percentage locations"
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        all_tbody = soup.find_all('tbody')
        
        # Count tbody elements with percentages
        tbody_with_pct = 0
        for tbody in all_tbody:
            if '%' in tbody.get_text():
                tbody_with_pct += 1
        
        return jsonify({
            "status": "OK",
            "total_tbody": len(all_tbody),
            "tbody_with_percentages": tbody_with_pct,
            "page_length": len(response.content)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

@app.route('/api/debug/tbody')
def debug_tbody():
    """Debug all tbody elements to find the right one"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        all_tbody = soup.find_all('tbody')
        tbody_info = []
        
        for idx, tbody in enumerate(all_tbody):
            tbody_text = tbody.get_text(strip=True)[:200]
            tbody_info.append({
                "index": idx,
                "class": tbody.get('class', []),
                "has_percentages": '%' in tbody.get_text(),
                "row_count": len(tbody.find_all('tr')),
                "sample_text": tbody_text,
                "looks_like_betting": '%' in tbody_text and 'ML RECORD' not in tbody_text.upper()
            })
        
        return jsonify({
            "total_tbody_count": len(all_tbody),
            "tbody_details": tbody_info
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

@app.route('/api/debug/percentages')
def debug_percentages():
    """Show where percentages are located in the HTML"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        percentage_info = []
        
        # Find all text nodes containing percentages
        for element in soup.find_all(text=re.compile(r'\d+%')):
            parent = element.parent
            grandparent = parent.parent if parent else None
            great_grandparent = grandparent.parent if grandparent else None
            
            info = {
                "percentage": element.strip(),
                "parent_tag": parent.name if parent else "None",
                "parent_class": parent.get('class', []) if parent else [],
                "grandparent_tag": grandparent.name if grandparent else "None",
                "grandparent_class": grandparent.get('class', []) if grandparent else [],
                "great_grandparent_tag": great_grandparent.name if great_grandparent else "None",
                "great_grandparent_class": great_grandparent.get('class', []) if great_grandparent else [],
                "context": parent.get_text(strip=True)[:100] if parent else ""
            }
            percentage_info.append(info)
        
        # Limit to first 15 for readability
        percentage_info = percentage_info[:15]
        
        return jsonify({
            "total_percentages_found": len(soup.find_all(text=re.compile(r'\d+%'))),
            "sample_percentages": percentage_info
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
