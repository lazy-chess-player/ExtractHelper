@echo off
call env_setup.bat
call conda activate extracthelper

cd /d D:\Code\Project\ExtractHelper
python -m app.ingest.ingest
python -m app.retrieval.build_index

echo DONE.
pause
