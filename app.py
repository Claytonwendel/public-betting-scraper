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
        
        # Look for elements containing team abbreviations AND percentages together
        # Common patterns: divs or sections with class names like 'game', 'matchup', 'betting', 'trends'
        potential_containers = soup.find_all(['div', 'section', 'article'], 
                                           class_=re.compile('game|matchup|betting|trend|sport|contest', re.I))
        
        logger.info(f"Found {len(potential_containers)} potential game containers")
        
        # Also look for any element that contains both team names and percentages
        all_elements = soup.find_all(['div', 'tr', 'section'])
        
        for element in all_elements:
            try:
                element_text = element.get_text(separator=' ', strip=True)
                
                # Skip if no percentages
                if '%' not in element_text:
                    continue
                
                # Count percentages
                percentages = re.findall(r'(\d+)%', element_text)
                if len(percentages) < 2:
                    continue
                
                # Look for valid MLB team abbreviations
                # Common MLB teams
                mlb_teams = ['NYY', 'BOS', 'TB', 'TOR', 'BAL', 'MIN', 'CLE', 'CWS', 'DET', 'KC',
                           'HOU', 'TEX', 'LAA', 'SEA', 'OAK', 'ATL', 'WSH', 'PHI', 'NYM', 'MIA',
                           'MIL', 'CHC', 'CIN', 'PIT', 'STL', 'LAD', 'SD', 'SF', 'COL', 'ARI',
                           'ANA', 'LA', 'CHW', 'CHI', 'WAS', 'TB', 'SD', 'SF']
                
                teams_found = []
                for team in mlb_teams:
                    if f' {team} ' in f' {element_text} ' or element_text.startswith(f'{team} ') or element_text.endswith(f' {team}'):
                        teams_found.append(team)
                
                # If we didn't find known teams, try to extract any 2-4 letter abbreviations
                if len(teams_found) < 2:
                    potential_teams = re.findall(r'\b([A-Z]{2,4})\b', element_text)
                    # Filter out non-team words
                    filtered_teams = [t for t in potential_teams if t not in 
                                    ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'ESPN', 'BET', 'ATS', 
                                     'DFS', 'UFC', 'MVP', 'DPOY', 'OROY', 'DROY', 'MLB', 'NBA', 
                                     'NFL', 'NHL', 'ML', 'OVER', 'UNDER', 'YES', 'NO', 'VS']]
                    teams_found.extend(filtered_teams)
                
                # Need at least 2 teams
                if len(teams_found) < 2:
                    continue
                
                # Extract time
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[apAP][mM])', element_text)
                game_time = time_match.group(1).upper() if time_match else 'TBD'
                
                # Create game data
                game_data = {
                    'game_time': game_time,
                    'away_team': teams_found[0],
                    'home_team': teams_found[1],
                    'moneyline_bets_pct': percentages[0] + '%' if len(percentages) > 0 else 'N/A',
                    'moneyline_money_pct': percentages[1] + '%' if len(percentages) > 1 else 'N/A',
                    'spread_bets_pct': percentages[2] + '%' if len(percentages) > 2 else 'N/A',
                    'spread_money_pct': percentages[3] + '%' if len(percentages) > 3 else 'N/A',
                    'total_bets_pct': percentages[4] + '%' if len(percentages) > 4 else 'N/A',
                    'total_money_pct': percentages[5] + '%' if len(percentages) > 5 else 'N/A',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Avoid duplicates
                if not any(g['away_team'] == game_data['away_team'] and g['home_team'] == game_data['home_team'] for g in games):
                    games.append(game_data)
                    logger.info(f"Found game: {game_data['away_team']} @ {game_data['home_team']}")
                
            except Exception as e:
                continue
        
        logger.info(f"Total unique games found: {len(games)}")
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
            "/api/debug/structure": "Debug page structure"
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
        
        title = soup.find('title')
        
        divs = len(soup.find_all('div'))
        tables = len(soup.find_all('table'))
        trs = len(soup.find_all('tr'))
        
        percent_elements = soup.find_all(text=re.compile(r'\d+%'))
        
        text = soup.get_text()
        teams = re.findall(r'\b([A-Z]{2,4})\b', text)
        teams = [t for t in teams if t not in ['PM', 'AM', 'ET', 'EST', 'MLB', 'NBA', 'NFL', 'NHL']][:20]
        
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

@app.route('/api/debug/structure')
def debug_structure():
    """Debug to find elements with percentages"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all elements containing percentages
        elements_with_pct = []
        
        for element in soup.find_all(text=re.compile(r'\d+%')):
            parent = element.parent
            if parent:
                # Get parent's tag and classes
                tag = parent.name
                classes = parent.get('class', [])
                
                # Get surrounding text
                parent_text = parent.get_text(strip=True)[:100]  # First 100 chars
                
                # Look for grandparent for more context
                grandparent = parent.parent
                gp_tag = grandparent.name if grandparent else 'None'
                gp_classes = grandparent.get('class', []) if grandparent else []
                
                elements_with_pct.append({
                    "percentage": element.strip(),
                    "parent_tag": tag,
                    "parent_classes": classes,
                    "grandparent_tag": gp_tag,
                    "grandparent_classes": gp_classes,
                    "context": parent_text
                })
        
        # Limit to first 10 for readability
        elements_with_pct = elements_with_pct[:10]
        
        # Also look for any divs with specific keywords
        betting_divs = soup.find_all('div', class_=re.compile('bet|trend|public|money|percent', re.I))
        
        return jsonify({
            "elements_with_percentages": elements_with_pct,
            "betting_div_count": len(betting_divs),
            "sample_betting_div_classes": [div.get('class', []) for div in betting_divs[:5]]
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
