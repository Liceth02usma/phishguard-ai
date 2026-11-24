@echo off
cd /d "C:\Users\Liceth Usma\Documents\.Semestre 10\creatividad_innovacion\proyecto_final2\phishguard-ai"
call .venv\Scripts\activate
python -m src.api --host 0.0.0.0 --port 8001