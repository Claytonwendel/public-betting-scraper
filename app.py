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
    """Scrape MLB betting data from SportsBettingDime"""
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
        
        # Look for game containers - these usually contain team names and betting data
        # Try multiple possible selectors based on common patterns
        game_containers = soup.find_all('div', class_=re.compile('game|matchup|contest|row'))
        
        # If no game containers, try table rows
        if not game_containers:
            game_containers = soup.find_all('tr', class_=re.compile('game|matchup|team'))
        
        # Also try data-attributes
        if not game_containers:
            game_containers = soup.find_all(['div', 'tr'], attrs={'data-game': True})
        
        logger.info(f"Found {len(game_containers)} potential game containers")
        
        # If still no containers, try to find by looking for team abbreviations
        if not game_containers:
            # Find all elements that might contain game data
            all_elements = soup.find_all(['div', 'tr', 'section'])
            
            for element in all_elements:
                text = element.get_text()
                # Check if element contains betting percentages and team names
                if '%' in text and re.search(r'\b[A-Z]{2,4}\b.*\b[A-Z]{2,4}\b', text):
                    game_containers.append(element)
        
        # Process each game container
        for idx, container in enumerate(game_containers):
            try:
                # Get all text from container
                container_text = container.get_text(separator=' ', strip=True)
                
                # Skip if no percentages found
                if '%' not in container_text:
                    continue
                
                # Extract time - look for time patterns
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[apAP][mM])', container_text)
                game_time = time_match.group(1).upper() if time_match else 'TBD'
                
                # Extract team abbreviations - look for 2-4 letter uppercase words
                teams = re.findall(r'\b([A-Z]{2,4})\b', container_text)
                
                # Filter out common non-team words
                non_teams = ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'MST', 'EDT', 'CDT', 'PDT', 'MDT', 'MLB', 'NBA', 'NFL', 'NHL']
                teams = [t for t in teams if t not in non_teams]
                
                if len(teams) < 2:
                    continue
                
                away_team = teams[0]
                home_team = teams[1]
                
                # Extract all percentages
                percentages = re.findall(r'(\d+)%', container_text)
                
                if len(percentages) < 2:
                    continue
                
                # Based on the structure you described:
                # Moneyline: first 2 percentages (bet%, $%)
                # Spread: next 2 percentages
                # Total: last 2 percentages
                
                game_data = {
                    'game_time': game_time,
                    'away_team': away_team,
                    'home_team': home_team,
                    'moneyline_bets_pct': percentages[0] + '%' if len(percentages) > 0 else 'N/A',
                    'moneyline_money_pct': percentages[1] + '%' if len(percentages) > 1 else 'N/A',
                    'spread_bets_pct': percentages[2] + '%' if len(percentages) > 2 else 'N/A',
                    'spread_money_pct': percentages[3] + '%' if len(percentages) > 3 else 'N/A',
                    'total_bets_pct': percentages[4] + '%' if len(percentages) > 4 else 'N/A',
                    'total_money_pct': percentages[5] + '%' if len(percentages) > 5 else 'N/A',
                    'timestamp': datetime.now().isoformat()
                }
                
                games.append(game_data)
                logger.info(f"Parsed game {idx + 1}: {away_team} @ {home_team}")
                
            except Exception as e:
                logger.error(f"Error parsing game container {idx}: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(games)} games")
        
        # If no games were parsed, let's try a more aggressive approach
        if not games:
            logger.info("No games found with standard parsing, trying alternative method...")
            
            # Look for any text that matches the pattern: TEAM1 XX% XX% TEAM2 XX% XX%
            full_text = soup.get_text()
            
            # Pattern to match game data
            pattern = r'(\d{1,2}:\d{2}\s*[apAP][mM])?\s*([A-Z]{2,4})\s+.*?(\d+)%\s+(\d+)%\s+([A-Z]{2,4})\s+.*?(\d+)%\s+(\d+)%'
            matches = re.finditer(pattern, full_text, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                groups = match.groups()
                game_data = {
                    'game_time': groups[0].upper() if groups[0] else 'TBD',
                    'away_team': groups[1],
                    'home_team': groups[4],
                    'moneyline_bets_pct': groups[2] + '%',
                    'moneyline_money_pct': groups[3] + '%',
                    'spread_bets_pct': 'N/A',
                    'spread_money_pct': 'N/A',
                    'total_bets_pct': 'N/A',
                    'total_money_pct': 'N/A',
                    'timestamp': datetime.now().isoformat()
                }
                games.append(game_data)
        
        # Return whatever we found (empty list is fine - means no games today)
        return games
        
    except Exception as e:
        logger.error(f"Error scraping MLB data: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
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
    # Scrape fresh data on each request
    data = scrape_mlb_data()
    
    # Log what we're returning
    logger.info(f"Returning {len(data)} games")
    
    return jsonify({
        "sport": "mlb",
        "data": data,
        "count": len(data),
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/debug')
def debug_info():
    """Debug endpoint to see what's happening with the scraper"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get page title
        title = soup.find('title')
        
        # Count various elements
        divs = len(soup.find_all('div'))
        tables = len(soup.find_all('table'))
        trs = len(soup.find_all('tr'))
        
        # Find elements with percentages
        percent_elements = soup.find_all(text=re.compile(r'\d+%'))
        
        # Find team abbreviations
        text = soup.get_text()
        teams = re.findall(r'\b([A-Z]{2,4})\b', text)
        teams = [t for t in teams if t not in ['PM', 'AM', 'ET', 'EST', 'MLB', 'NBA', 'NFL', 'NHL']][:20]  # First 20
        
        return jsonify({
            "status": "OK",
            "page_title": title.text if title else "No title",
            "element_counts": {
                "divs": divs,
                "tables": tables,
                "trs": trs,
                "percent_elements": len(percent_elements)
            },
            "sample_teams": teams,
            "response_length": len(response.content)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
