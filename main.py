import os
import sys
import asyncio
import logging
from pathlib import Path

import yaml
from dotenv import load_dotenv

from database import Database
from ai_client import GrokClient
from bot_manager import BotManager
from dialog_engine import DialogEngine
from control_bot import ControlBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)


def validate_environment(control_bot_enabled: bool = False):
    """Validate that required environment variables are set"""
    required_vars = ['API_ID', 'API_HASH', 'GROK_API_KEY', 'GROK_API_URL']

    if control_bot_enabled:
        required_vars.append('CONTROL_BOT_TOKEN')

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please create a .env file based on .env.example")
        sys.exit(1)


async def run_control_bot(config: dict, db: Database):
    """Запуск Control Bot окремо"""
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    bot_token = os.getenv('CONTROL_BOT_TOKEN')

    control_config = config.get('control_bot', {})
    admin_user_ids = control_config.get('admin_user_ids', [])

    if not admin_user_ids:
        logger.error("No admin_user_ids specified in config.yaml for control bot")
        logger.error("Please add your Telegram user ID to config.yaml")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Starting Control Bot (Management Mode)")
    logger.info("=" * 60)
    logger.info(f"Admin users: {admin_user_ids}")

    control_bot = ControlBot(
        bot_token=bot_token,
        api_id=api_id,
        api_hash=api_hash,
        db=db,
        admin_user_ids=admin_user_ids
    )

    try:
        await control_bot.start()
    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await control_bot.stop()
        logger.info("Control Bot stopped")


async def run_dialog_system(config: dict, db: Database):
    """Запуск Dialog System з юзерботами"""
    api_id = int(os.getenv('API_ID'))
    api_hash = os.getenv('API_HASH')
    grok_api_key = os.getenv('GROK_API_KEY')
    grok_api_url = os.getenv('GROK_API_URL')

    group_id = config['group_id']
    prompt = config['prompt']
    min_delay = config['delays']['min_seconds']
    max_delay = config['delays']['max_seconds']
    max_context = config['max_context_messages']

    # Initialize components
    logger.info("Initializing components...")

    # Bot Manager
    bot_manager = BotManager(
        api_id=api_id,
        api_hash=api_hash,
        db=db
    )

    try:
        # Load sessions
        logger.info("Loading Telegram sessions...")
        await bot_manager.load_sessions()

        if not bot_manager.get_all_clients():
            logger.error("No active sessions found!")
            logger.error("Please add sessions using Control Bot first")
            logger.error("Run: python main.py --control")
            return

        # Initialize AI client
        logger.info("Initializing Grok AI client...")
        ai_client = GrokClient(grok_api_key, grok_api_url)

        # Initialize dialog engine
        logger.info("Initializing dialog engine...")
        dialog_engine = DialogEngine(
            bot_manager=bot_manager,
            ai_client=ai_client,
            group_id=group_id,
            prompt=prompt,
            min_delay=min_delay,
            max_delay=max_delay,
            max_context=max_context
        )

        logger.info("=" * 60)
        logger.info("All components initialized successfully!")
        logger.info(f"Target group ID: {group_id}")
        logger.info(f"Active clients: {len(bot_manager.get_all_clients())}")
        logger.info(f"Message delay: {min_delay}-{max_delay} seconds")
        logger.info("=" * 60)

        # Start dialog engine
        logger.info("Starting dialog engine...")
        await dialog_engine.run()

    except KeyboardInterrupt:
        logger.info("\nReceived shutdown signal (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        if 'dialog_engine' in locals():
            dialog_engine.stop()
        if 'bot_manager' in locals():
            await bot_manager.disconnect_all()
        if 'ai_client' in locals() and ai_client.session:
            await ai_client.session.close()

        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='IBotServe - Telegram Userbot System')
    parser.add_argument(
        '--control',
        action='store_true',
        help='Run in control bot mode (for managing userbots)'
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Starting IBotServe - Telegram Userbot System")
    logger.info("=" * 60)

    # Load environment variables
    load_dotenv()

    # Load configuration
    config = load_config()

    # Check if control bot mode is requested
    control_mode = args.control
    if not control_mode:
        control_config = config.get('control_bot', {})
        control_mode = control_config.get('enabled', False) and args.control

    # Validate environment
    validate_environment(control_bot_enabled=control_mode)

    # Initialize database
    logger.info("Initializing database...")
    db = Database()

    try:
        if control_mode or args.control:
            # Run control bot
            await run_control_bot(config, db)
        else:
            # Run dialog system
            await run_dialog_system(config, db)
    finally:
        db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
