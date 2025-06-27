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
    """Scrape MLB betting data from anywhere on the page"""
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
        
        # Strategy 1: Look for divs/sections containing percentages
        elements_with_percentages = []
        
        # Find all elements containing percentage text
        for element in soup.find_all(text=re.compile(r'\d+%')):
            parent = element.parent
            # Go up the tree to find a meaningful container
            while parent and parent.name in ['span', 'b', 'strong', 'em', 'i']:
                parent = parent.parent
            
            if parent and parent not in elements_with_percentages:
                # Check if this parent contains multiple percentages (likely a game)
                parent_text = parent.get_text()
                pct_count = len(re.findall(r'\d+%', parent_text))
                if pct_count >= 2:  # At least 2 percentages
                    elements_with_percentages.append(parent)
        
        logger.info(f"Found {len(elements_with_percentages)} elements with multiple percentages")
        
        # Process each element that might be a game
        for element in elements_with_percentages:
            try:
                text = element.get_text(separator=' ', strip=True)
                
                # Skip if it's the ML record table
                if 'ML RECORD' in text.upper() or 'DATE' in text.upper():
                    continue
                
                # Extract all percentages
                percentages = re.findall(r'(\d+)%', text)
                if len(percentages) < 2:
                    continue
                
                # Look for time pattern
                time_match = re.search(r'(\w+ \d+,?\s*\d{1,2}:\d{2}\s*[AP]M)', text)
                if not time_match:
                    time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text)
                game_time = time_match.group(1) if time_match else 'TBD'
                
                # Extract team abbreviations
                # Common MLB teams
                mlb_teams = ['NYY', 'BOS', 'TB', 'TOR', 'BAL', 'MIN', 'CLE', 'CWS', 'DET', 'KC',
                           'HOU', 'TEX', 'LAA', 'SEA', 'OAK', 'ATL', 'WSH', 'PHI', 'NYM', 'MIA',
                           'MIL', 'CHC', 'CIN', 'PIT', 'STL', 'LAD', 'SD', 'SF', 'COL', 'ARI',
                           'ANA', 'LA', 'CHW', 'CHI', 'WAS', 'TBR', 'SDP', 'SFG']
                
                teams_found = []
                for team in mlb_teams:
                    if team in text:
                        teams_found.append(team)
                
                # If no known teams found, try generic pattern
                if len(teams_found) < 2:
                    all_caps = re.findall(r'\b([A-Z]{2,4})\b', text)
                    non_teams = ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'EDT', 'CDT', 'PDT', 'MDT', 
                                'PT', 'CT', 'MT', 'ESPN', 'BET', 'ATS', 'DFS', 'UFC', 'MVP', 'DPOY', 
                                'OROY', 'DROY', 'MLB', 'NBA', 'NFL', 'NHL', 'OVER', 'UNDER', 'YES', 
                                'NO', 'VS', 'ML', 'RECORD', 'DATE', 'TBD']
                    potential_teams = [t for t in all_caps if t not in non_teams]
                    teams_found.extend(potential_teams)
                
                if len(teams_found) >= 2 and len(percentages) >= 2:
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
                    if not any(g['away_team'] == game_data['away_team'] and 
                             g['home_team'] == game_data['home_team'] for g in games):
                        games.append(game_data)
                        logger.info(f"Found game: {teams_found[0]} @ {teams_found[1]}")
                
            except Exception as e:
                logger.error(f"Error processing element: {str(e)}")
                continue
        
        # Strategy 2: Look for specific class patterns if no games found
        if not games:
            logger.info("Trying alternative search patterns...")
            
            # Common class patterns for betting data
            possible_selectors = [
                'div[class*="game"]',
                'div[class*="match"]',
                'div[class*="betting"]',
                'div[class*="public"]',
                'div[class*="percent"]',
                'tr[class*="game"]',
                'tr[class*="match"]',
                'section[class*="game"]',
                'article[class*="game"]'
            ]
            
            for selector in possible_selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    text = element.get_text()
                    percentages = re.findall(r'(\d+)%', text)
                    
                    if len(percentages) >= 2:
                        # Extract teams and time similar to above
                        all_caps = re.findall(r'\b([A-Z]{2,4})\b', text)
                        teams = [t for t in all_caps if t not in ['PM', 'AM', 'ET', 'EST', 'MLB', 'NBA', 'NFL', 'NHL']]
                        
                        if len(teams) >= 2:
                            time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text)
                            game_time = time_match.group(1) if time_match else 'TBD'
                            
                            game_data = {
                                'game_time': game_time,
                                'away_team': teams[0],
                                'home_team': teams[1],
                                'moneyline_bets_pct': percentages[0] + '%',
                                'moneyline_money_pct': percentages[1] + '%' if len(percentages) > 1 else 'N/A',
                                'spread_bets_pct': percentages[2] + '%' if len(percentages) > 2 else 'N/A',
                                'spread_money_pct': percentages[3] + '%' if len(percentages) > 3 else 'N/A',
                                'total_bets_pct': percentages[4] + '%' if len(percentages) > 4 else 'N/A',
                                'total_money_pct': percentages[5] + '%' if len(percentages) > 5 else 'N/A',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if not any(g['away_team'] == game_data['away_team'] and 
                                     g['home_team'] == game_data['home_team'] for g in games):
                                games.append(game_data)
        
        logger.info(f"Total games found: {len(games)}")
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
            "/api/debug/full": "Full diagnostic information",
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
        
        # Check for various tbody classes
        tbody_with_text = soup.find_all('tbody', class_=re.compile('text'))
        all_tbody = soup.find_all('tbody')
        
        # Check all tbody classes
        tbody_classes = []
        for tb in all_tbody[:5]:  # First 5
            classes = tb.get('class', [])
            tbody_classes.append(classes)
        
        return jsonify({
            "status": "OK",
            "tbody_with_text_class": len(tbody_with_text),
            "total_tbody": len(all_tbody),
            "sample_tbody_classes": tbody_classes,
            "page_length": len(response.content)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

@app.route('/api/debug/tbody')
def debug_tbody():
    """Debug the actual tbody content"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get the tbody
        tbody = soup.find('tbody')
        if not tbody:
            return jsonify({"error": "No tbody found"})
        
        # Get first 10 rows
        rows = tbody.find_all('tr')[:10]
        
        row_data = []
        for idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            row_data.append({
                "row": idx,
                "cell_count": len(cells),
                "text": row.get_text(strip=True)[:200],  # First 200 chars
                "has_percentage": '%' in row.get_text()
            })
        
        return jsonify({
            "tbody_found": True,
            "total_rows": len(tbody.find_all('tr')),
            "sample_rows": row_data
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

@app.route('/api/debug/full')
def debug_full():
    """More comprehensive debugging"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check if we're getting the right page
        title = soup.find('title')
        
        # Look for any betting-related content
        betting_keywords = ['moneyline', 'spread', 'total', 'bet%', 'betting', 'public']
        keyword_found = any(keyword in soup.text.lower() for keyword in betting_keywords)
        
        # Check for JavaScript content
        scripts = soup.find_all('script')
        has_react = any('react' in str(script).lower() for script in scripts)
        has_vue = any('vue' in str(script).lower() for script in scripts)
        
        # Sample of body content
        body_text = soup.get_text()[:500]
        
        # Look for specific patterns
        has_percentages = bool(re.search(r'\d+%', body_text))
        team_pattern = re.findall(r'\b([A-Z]{2,4})\b', body_text)
        
        return jsonify({
            "page_title": title.text if title else "No title",
            "has_betting_keywords": keyword_found,
            "has_react": has_react,
            "has_vue": has_vue,
            "has_percentages": has_percentages,
            "sample_teams_found": team_pattern[:10],
            "response_status": response.status_code,
            "content_length": len(response.content),
            "sample_content": body_text,
            "script_count": len(scripts)
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
