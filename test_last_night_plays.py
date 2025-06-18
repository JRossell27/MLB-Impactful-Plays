#!/usr/bin/env python3
"""
Test Script: Process Last Night's High-Impact Plays
Finds all plays from June 17, 2025 that meet the 40% WP threshold
and processes them through the complete GIF creation and posting pipeline
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from enhanced_impact_tracker import EnhancedImpactTracker

# Configure logging for test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_last_night_plays.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class LastNightPlayTester:
    def __init__(self):
        self.tracker = EnhancedImpactTracker()
        self.test_date = "2025-06-17"  # Last night
        self.found_plays = []
        
    def get_games_from_date(self, date_str: str):
        """Get all games from a specific date"""
        try:
            url = f"{self.tracker.schedule_api_base}/schedule"
            params = {
                'sportId': 1,
                'date': date_str,
                'hydrate': 'linescore,decisions,team',
                'useLatestGames': 'false',
                'language': 'en'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            games = []
            
            for date_data in data.get('dates', []):
                for game in date_data.get('games', []):
                    status = game.get('status', {}).get('statusCode', '')
                    # Include finished games
                    if status in ['F', 'O']:  # Final, Final-Other
                        games.append(game)
            
            logger.info(f"Found {len(games)} completed games from {date_str}")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games from {date_str}: {e}")
            return []
    
    def find_high_impact_plays(self):
        """Find all high-impact plays from last night"""
        logger.info(f"🔍 Searching for high-impact plays from {self.test_date}")
        
        games = self.get_games_from_date(self.test_date)
        total_plays_checked = 0
        high_impact_count = 0
        
        for game in games:
            game_id = game.get('gamePk')
            if not game_id:
                continue
                
            game_info = {
                'home_team': game.get('teams', {}).get('home', {}).get('team', {}).get('abbreviation', 'HOME'),
                'away_team': game.get('teams', {}).get('away', {}).get('team', {}).get('abbreviation', 'AWAY'),
                'status': game.get('status', {}).get('statusCode', ''),
                'game_id': game_id,
                'final_score': f"{game.get('teams', {}).get('away', {}).get('score', 0)}-{game.get('teams', {}).get('home', {}).get('score', 0)}"
            }
            
            logger.info(f"📊 Analyzing {game_info['away_team']} @ {game_info['home_team']} (Final: {game_info['final_score']})")
            
            # Get all plays from this game
            plays = self.tracker.get_game_plays(game_id)
            total_plays_checked += len(plays)
            
            for play in plays:
                # STEP 1: Enhance play with Baseball Savant WP% data
                savant_data = self.tracker.get_enhanced_wp_data_from_savant(game_id, play)
                if savant_data and 'delta_home_win_exp' in savant_data:
                    play['delta_home_win_exp'] = savant_data['delta_home_win_exp']
                    logger.info(f"  📈 Found Baseball Savant WP%: {savant_data['delta_home_win_exp']:.1%} for {play.get('event', 'Unknown')}")
                
                # STEP 2: Calculate impact score
                impact_score = self.tracker.calculate_impact_score(play)
                
                # STEP 3: Check if it meets the threshold
                if self.tracker.is_high_impact_play(impact_score, play.get('leverage_index', 1.0)):
                    high_impact_count += 1
                    
                    play_summary = {
                        'game_id': game_id,
                        'game_info': game_info,
                        'play': play,
                        'impact_score': impact_score,
                        'description': play.get('description', ''),
                        'event': play.get('event', ''),
                        'inning': play.get('inning', 0),
                        'half_inning': play.get('half_inning', ''),
                        'batter': play.get('batter', ''),
                        'leverage': play.get('leverage_index', 1.0)
                    }
                    
                    self.found_plays.append(play_summary)
                    
                    logger.info(f"⭐ HIGH-IMPACT PLAY FOUND!")
                    logger.info(f"   Game: {game_info['away_team']} @ {game_info['home_team']}")
                    logger.info(f"   Play: {play.get('event', 'Unknown')} - {play.get('description', '')}")
                    logger.info(f"   Impact: {impact_score:.1%} WP change")
                    logger.info(f"   Inning: {play.get('half_inning', '')} {play.get('inning', 0)}")
                    logger.info(f"   Leverage: {play.get('leverage_index', 1.0):.2f}")
        
        logger.info(f"📊 SEARCH COMPLETE:")
        logger.info(f"   Total games checked: {len(games)}")
        logger.info(f"   Total plays analyzed: {total_plays_checked}")
        logger.info(f"   High-impact plays found: {high_impact_count}")
        
        return self.found_plays
    
    def process_found_plays(self):
        """Process each found play through the complete pipeline"""
        if not self.found_plays:
            logger.info("No high-impact plays found to process")
            return
        
        logger.info(f"🎬 Starting end-to-end processing of {len(self.found_plays)} high-impact plays...")
        
        # Check Twitter connection
        if not self.tracker.twitter_api:
            logger.warning("⚠️  Twitter API not connected - will create GIFs but skip posting")
            logger.info("   Set Twitter environment variables to enable posting:")
            logger.info("   TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
        
        successful_gifs = 0
        successful_posts = 0
        
        for i, play_data in enumerate(self.found_plays, 1):
            logger.info(f"\n🎯 Processing play {i}/{len(self.found_plays)}")
            logger.info(f"   {play_data['event']} - {play_data['impact_score']:.1%} impact")
            logger.info(f"   {play_data['game_info']['away_team']} @ {play_data['game_info']['home_team']}")
            
            try:
                # Queue the play using the normal system
                queued = self.tracker.queue_high_impact_play(
                    play_data['play'], 
                    play_data['game_info'], 
                    play_data['impact_score']
                )
                
                if queued:
                    logger.info(f"   ✅ Play queued successfully")
                    
                    # Try to create GIF immediately for testing
                    queued_play = self.tracker.play_queue[-1]  # Get the just-added play
                    
                    logger.info(f"   🎬 Attempting GIF creation...")
                    
                    gif_path = self.tracker.gif_integration.get_gif_for_play(
                        game_id=queued_play.game_id,
                        play_id=queued_play.mlb_play_data.get('atBatIndex', 0),
                        game_date=queued_play.game_date,
                        mlb_play_data=queued_play.mlb_play_data
                    )
                    
                    if gif_path and os.path.exists(gif_path):
                        successful_gifs += 1
                        queued_play.gif_created = True
                        queued_play.gif_path = gif_path
                        
                        logger.info(f"   ✅ GIF created: {gif_path}")
                        
                        # Try to post if Twitter is available
                        if self.tracker.twitter_api:
                            logger.info(f"   🐦 Attempting to post to Twitter...")
                            
                            if self.tracker.post_complete_tweet_with_gif(queued_play):
                                successful_posts += 1
                                logger.info(f"   ✅ Tweet posted successfully!")
                            else:
                                logger.error(f"   ❌ Tweet posting failed")
                        else:
                            logger.info(f"   ⏭️  Skipping Twitter post (API not connected)")
                    else:
                        logger.warning(f"   ⏳ GIF not available yet")
                else:
                    logger.error(f"   ❌ Failed to queue play")
                
                # Small delay between plays to avoid overwhelming APIs
                if i < len(self.found_plays):
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing play: {e}")
        
        # Final summary
        logger.info(f"\n🎉 END-TO-END TEST COMPLETE!")
        logger.info(f"   Plays found: {len(self.found_plays)}")
        logger.info(f"   GIFs created: {successful_gifs}")
        logger.info(f"   Tweets posted: {successful_posts}")
        logger.info(f"   Success rate: {(successful_gifs/len(self.found_plays)*100):.1f}% GIFs, {(successful_posts/len(self.found_plays)*100):.1f}% tweets")
        
        # Save results for review
        results = {
            'test_date': self.test_date,
            'total_plays_found': len(self.found_plays),
            'successful_gifs': successful_gifs,
            'successful_posts': successful_posts,
            'plays': [
                {
                    'game': f"{p['game_info']['away_team']} @ {p['game_info']['home_team']}",
                    'event': p['event'],
                    'impact': f"{p['impact_score']:.1%}",
                    'inning': f"{p['half_inning']} {p['inning']}",
                    'description': p['description']
                }
                for p in self.found_plays
            ]
        }
        
        with open(f'test_results_{self.test_date}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"   Results saved to: test_results_{self.test_date}.json")

def main():
    """Run the test"""
    logger.info("🧪 STARTING LAST NIGHT'S HIGH-IMPACT PLAYS TEST")
    logger.info("=" * 60)
    
    tester = LastNightPlayTester()
    
    # Step 1: Find all high-impact plays
    logger.info("STEP 1: Finding high-impact plays from last night...")
    found_plays = tester.find_high_impact_plays()
    
    if not found_plays:
        logger.info("❌ No high-impact plays found meeting the 40% threshold")
        logger.info("   This could mean:")
        logger.info("   - No games had plays over 40% WP impact")
        logger.info("   - Baseball Savant data not available for that date")
        logger.info("   - All high-impact moments had lower WP changes")
        return
    
    # Step 2: Process them through the pipeline
    logger.info(f"\nSTEP 2: Processing {len(found_plays)} plays through complete pipeline...")
    tester.process_found_plays()
    
    logger.info("\n🎉 Test complete! Check the log files and results for details.")

if __name__ == "__main__":
    main() 