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
    """Scrape MLB betting data from SportsBettingDime table"""
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
        
        # Find the main table (debug showed 1 table with 32 rows)
        table = soup.find('table')
        
        if not table:
            logger.error("No table found on page")
            return []
        
        # Get all rows from the table
        rows = table.find_all('tr')
        logger.info(f"Found table with {len(rows)} rows")
        
        # Skip header row(s) and process game rows
        for idx, row in enumerate(rows):
            try:
                # Get all cells in the row
                cells = row.find_all(['td', 'th'])
                
                if len(cells) < 6:  # Need enough cells for game data
                    continue
                
                # Get text from each cell
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # Skip if this looks like a header row
                if any(header in ' '.join(cell_texts).lower() for header in ['matchup', 'moneyline', 'spread', 'total', 'team']):
                    continue
                
                # Log row data for debugging
                logger.info(f"Row {idx}: {cell_texts[:8]}")  # Log first 8 cells
                
                # Look for team abbreviations in the first few cells
                teams = []
                for text in cell_texts[:4]:  # Check first 4 cells for teams
                    # Match 2-4 letter uppercase abbreviations
                    team_match = re.search(r'\b([A-Z]{2,4})\b', text)
                    if team_match:
                        team = team_match.group(1)
                        # Filter out known non-team abbreviations
                        if team not in ['PM', 'AM', 'ET', 'EST', 'CST', 'PST', 'ESPN', 'BET', 'ATS', 'DFS', 'UFC', 'MVP', 'DPOY', 'OROY', 'DROY', 'MLB', 'NBA', 'NFL', 'NHL']:
                            teams.append(team)
                
                if len(teams) < 2:
                    continue
                
                # Extract time from the row
                time_text = ' '.join(cell_texts[:2])  # Time might be in first cells
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[apAP][mM])', time_text)
                game_time = time_match.group(1).upper() if time_match else 'TBD'
                
                # Extract percentages from the row
                percentages = []
                for text in cell_texts:
                    pct_matches = re.findall(r'(\d+)%', text)
                    percentages.extend(pct_matches)
                
                if len(percentages) < 2:
                    continue
                
                # Create game data
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
                logger.info(f"Successfully parsed game: {teams[0]} @ {teams[1]}")
                
            except Exception as e:
                logger.error(f"Error parsing row {idx}: {str(e)}")
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
            "/api/debug/table": "Debug table structure"
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

@app.route('/api/debug/table')
def debug_table():
    """Debug table structure specifically"""
    try:
        url = "https://www.sportsbettingdime.com/mlb/public-betting-trends/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            return jsonify({"error": "No table found"})
        
        # Get first 5 rows to understand structure
        rows = table.find_all('tr')[:5]
        
        row_data = []
        for idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            row_data.append({
                "row": idx,
                "cell_count": len(cells),
                "cells": cell_texts[:10]  # First 10 cells
            })
        
        # Also check for specific classes or attributes
        table_classes = table.get('class', [])
        table_id = table.get('id', '')
        
        return jsonify({
            "table_found": True,
            "table_classes": table_classes,
            "table_id": table_id,
            "total_rows": len(table.find_all('tr')),
            "sample_rows": row_data
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        })

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
