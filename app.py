import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
from typing import Dict, List, Optional
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global variable to store scraped data
cached_data = {
    'mlb': []
}

def scrape_mlb_data():
    """Scrape MLB betting data - simplified version"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        games = []
        
        # This is a simplified scraper - you may need to adjust selectors
        # based on the actual website structure
        game_elements = soup.find_all(['div', 'tr'], class_=re.compile('game|match|row'))
        
        for element in game_elements[:10]:  # Limit to first 10 games
            try:
                text = element.get_text()
                
                # Extract team abbreviations (3-4 letter uppercase words)
                teams = re.findall(r'\b[A-Z]{2,4}\b', text)
                if len(teams) < 2:
                    continue
                
                # Extract percentages
                percentages = re.findall(r'(\d+)%', text)
                
                # Extract time if available
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', text)
                game_time = time_match.group(1) if time_match else "TBD"
                
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
                
            except Exception as e:
                logger.error(f"Error parsing game: {e}")
                continue
        
        # If no games found, return sample data
        if not games:
            games = [
                {
                    'game_time': '7:10 PM',
                    'away_team': 'NYY',
                    'home_team': 'BOS',
                    'moneyline_bets_pct': '45%',
                    'moneyline_money_pct': '42%',
                    'spread_bets_pct': '48%',
                    'spread_money_pct': '46%',
                    'total_bets_pct': '52%',
                    'total_money_pct': '54%',
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'game_time': '7:05 PM',
                    'away_team': 'TB',
                    'home_team': 'TOR',
                    'moneyline_bets_pct': '62%',
                    'moneyline_money_pct': '58%',
                    'spread_bets_pct': '55%',
                    'spread_money_pct': '53%',
                    'total_bets_pct': '48%',
                    'total_money_pct': '51%',
                    'timestamp': datetime.now().isoformat()
                }
            ]
        
        return games
        
    except Exception as e:
        logger.error(f"Error scraping MLB data: {e}")
        # Return sample data on error
        return [
            {
                'game_time': '7:10 PM',
                'away_team': 'NYY',
                'home_team': 'BOS',
                'moneyline_bets_pct': '45%',
                'moneyline_money_pct': '42%',
                'spread_bets_pct': '48%',
                'spread_money_pct': '46%',
                'total_bets_pct': '52%',
                'total_money_pct': '54%',
                'timestamp': datetime.now().isoformat()
            }
        ]

def update_data():
    """Update betting data"""
    global cached_data
    logger.info("Updating betting data...")
    
    try:
        mlb_games = scrape_mlb_data()
        cached_data['mlb'] = mlb_games
        logger.info(f"Updated MLB data with {len(mlb_games)} games")
    except Exception as e:
        logger.error(f"Error updating data: {e}")

# Set up scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting
atexit.register(lambda: scheduler.shutdown())

# Initial data load
update_data()

@app.route('/')
def home():
    return jsonify({
        "message": "Sports Betting API",
        "endpoints": {
            "/api/health": "Health check",
            "/api/betting/mlb": "Get MLB betting data",
            "/api/betting/all": "Get all sports data",
            "/api/refresh": "Manually refresh data"
        }
    })

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "sports_available": list(cached_data.keys()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/betting/mlb')
def get_mlb_data():
    return jsonify({
        "sport": "mlb",
        "data": cached_data.get('mlb', []),
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/betting/all')
def get_all_data():
    return jsonify({
        "data": cached_data,
        "last_updated": datetime.now().isoformat()
    })

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    update_data()
    return jsonify({"message": "Data refresh initiated"})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
