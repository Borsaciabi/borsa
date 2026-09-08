import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.bot import main

if __name__ == "__main__":
    main()
