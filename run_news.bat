@echo off
cd /d "D:\Claude Code\News"
python news_sender.py >> "D:\Claude Code\News\log.txt" 2>&1
