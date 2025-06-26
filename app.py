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
    """Scrape MLB betting data with multiple fallback strategies"""
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
        
        # Strategy 1: Look for tbody with any class containing "text"
        game_bodies = soup.find_all('tbody', class_=re.compile('text'))
        logger.info(f"Found {len(game_bodies)} tbody elements with 'text' in class")
        
        # Strategy 2: Look for any tbody elements
        if not game_bodies:
            game_bodies = soup.find_all('tbody')
            logger.info(f"Found {len(game_bodies)} total tbody elements")
        
        # Strategy 3: Look for elements containing team names and percentages
        if not game_bodies:
            # Find all elements that contain percentages
            elements_with_pct = []
            for elem in soup.find_all(text=re.compile(r'\d+%')):
                parent = elem.parent
                while parent and parent.name not in ['tbody', 'table', 'div']:
                    parent = parent.parent
                if parent and parent not in elements_with_pct:
                    elements_with_pct.append(parent)
            
            logger.info(f"Found {len(elements_with_pct)} elements containing percentages")
            game_bodies = elements_with_pct
        
        # Process whatever we found
        for idx, element in enumerate(game_bodies[:10]):  # Limit to first 10
            try:
                # Get all text from the element
                text = element.get_text(separator=' ', strip=True)
                
                # Look for patterns that indicate game data
                if '%' not in text:
                    continue
                
                # Extract percentages
                percentages = re.findall(r'(\d+)%', text)
                if len(percentages) < 2:
                    continue
                
                # Look for time
                time_match = re.search(r'(\w+ \d+,?\s*\d{1,2}:\d{2}\s*[AP]M)', text)
                if not time_match:
                    time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text)
                game_time = time_match.group(1) if time_match else 'TBD'
                
                # Look for team abbreviations
                teams = re.findall(r'\b([A-Z]{2,4})\b', text)
                teams = [t for t in teams if t not in ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'EDT', 'CDT', 'PDT', 'MDT', 'PT', 'CT', 'MT', 'ESPN', 'BET', 'ATS', 'DFS', 'UFC', 'MVP', 'DPOY', 'OROY', 'DROY', 'MLB', 'NBA', 'NFL', 'NHL', 'OVER', 'UNDER']]
                
                if len(teams) >= 2:
                    game_data = {
                        'game_time': game_time,
                        'away_team': teams[0],
                        'home_team': teams[1],
                        'moneyline_bets_pct': percentages[0] + '%' if len(percentages) > 0 else 'N/A',
                        'moneyline_money_pct': percentages[1] + '%' if len(percentages) > 1 else 'N/A',
                        'spread_bets_pct': percentages[2] + '%' if len(percentages) > 2 else 'N/A',
                        'spread_money_pct': percentages[3] + '%' if len(percentages) > 3 else 'N/A',
                        'total_bets_pct': percentages[4] + '%' if len(percentages) > 4 else 'N/A',
                        'total_money_pct': percentages[5] + '%' if len(percentages) > 5 else 'N/A',
                        'timestamp': datetime.now().isoformat()
                    }
                    games.append(game_data)
                    logger.info(f"Found game: {teams[0]} @ {teams[1]}")
                
            except Exception as e:
                logger.error(f"Error parsing element {idx}: {str(e)}")
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
            "/api/debug/full": "Full diagnostic information"
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

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
