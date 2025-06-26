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
    """Scrape MLB betting data looking for tbody without class requirements"""
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
        
        # Find ALL tbody elements, regardless of class
        all_tbody = soup.find_all('tbody')
        logger.info(f"Found {len(all_tbody)} tbody elements")
        
        # Process the tbody we found (there's only 1 according to debug)
        if all_tbody:
            tbody = all_tbody[0]  # Get the first (and only) tbody
            
            # Get all rows in this tbody
            rows = tbody.find_all('tr')
            logger.info(f"Found {len(rows)} rows in tbody")
            
            # Group rows by 3 (date/time row, away team row, home team row)
            i = 0
            while i < len(rows) - 2:
                try:
                    # Check if this looks like a game group
                    row1_text = rows[i].get_text(strip=True)
                    row2_text = rows[i+1].get_text(strip=True) if i+1 < len(rows) else ""
                    row3_text = rows[i+2].get_text(strip=True) if i+2 < len(rows) else ""
                    
                    # Look for date/time pattern in first row
                    time_match = re.search(r'(\w+ \d+,?\s*\d{1,2}:\d{2}\s*[AP]M)', row1_text)
                    if not time_match:
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', row1_text)
                    
                    # Check if rows 2 and 3 have percentages (indicating team rows)
                    if time_match and '%' in row2_text and '%' in row3_text:
                        game_time = time_match.group(1)
                        
                        # Process away team (row 2)
                        away_cells = rows[i+1].find_all(['td', 'th'])
                        away_text = rows[i+1].get_text(strip=True)
                        away_percentages = re.findall(r'(\d+)%', away_text)
                        
                        # Process home team (row 3)
                        home_cells = rows[i+2].find_all(['td', 'th'])
                        home_text = rows[i+2].get_text(strip=True)
                        home_percentages = re.findall(r'(\d+)%', home_text)
                        
                        # Extract team names
                        away_teams = re.findall(r'\b([A-Z]{2,4})\b', away_text)
                        home_teams = re.findall(r'\b([A-Z]{2,4})\b', home_text)
                        
                        # Filter out non-team abbreviations
                        non_teams = ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'EDT', 'CDT', 'PDT', 'MDT', 'PT', 'CT', 'MT', 'ESPN', 'BET', 'ATS', 'DFS', 'UFC', 'MVP', 'DPOY', 'OROY', 'DROY', 'MLB', 'NBA', 'NFL', 'NHL', 'OVER', 'UNDER', 'YES', 'NO', 'VS']
                        away_teams = [t for t in away_teams if t not in non_teams]
                        home_teams = [t for t in home_teams if t not in non_teams]
                        
                        if away_teams and home_teams and len(away_percentages) >= 2 and len(home_percentages) >= 2:
                            game_data = {
                                'game_time': game_time,
                                'away_team': away_teams[0],
                                'home_team': home_teams[0],
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
                                # Simplified fields for frontend compatibility
                                'moneyline_bets_pct': away_percentages[0] + '%' if len(away_percentages) > 0 else 'N/A',
                                'moneyline_money_pct': away_percentages[1] + '%' if len(away_percentages) > 1 else 'N/A',
                                'spread_bets_pct': away_percentages[2] + '%' if len(away_percentages) > 2 else 'N/A',
                                'spread_money_pct': away_percentages[3] + '%' if len(away_percentages) > 3 else 'N/A',
                                'total_bets_pct': away_percentages[4] + '%' if len(away_percentages) > 4 else 'N/A',
                                'total_money_pct': away_percentages[5] + '%' if len(away_percentages) > 5 else 'N/A',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            games.append(game_data)
                            logger.info(f"Successfully parsed game: {away_teams[0]} @ {home_teams[0]} at {game_time}")
                            
                            # Skip next 2 rows since we processed them
                            i += 3
                            continue
                    
                    i += 1
                    
                except Exception as e:
                    logger.error(f"Error parsing rows starting at {i}: {str(e)}")
                    i += 1
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
            "/api/debug/full": "Full diagnostic information",
            "/api/debug/tbody": "Debug tbody content"
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

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
