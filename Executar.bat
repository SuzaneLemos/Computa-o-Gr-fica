@echo off
REM -----------------------------------------
REM Instalando Paint Trevoso
REM -----------------------------------------

REM --- Pasta onde o .bat está localizado ---
set BASE_DIR=%~dp0
echo Base do projeto: %BASE_DIR%
echo.

REM --- Passo 1: Criar ambiente virtual se nao existir ---
if not exist "%BASE_DIR%\.venv" (
    echo [25%%] Criando ambiente virtual...
    python -m venv "%BASE_DIR%\.venv"
) else (
    echo [25%%] Ambiente virtual ja existe. Pulando criacao...
)
echo.

REM --- Passo 2: Atualizar pip no Python da venv ---
echo [50%%] Atualizando pip na venv...
"%BASE_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip
echo.

REM --- Passo 3: Instalar dependencias do requirements.txt ---
if exist "%BASE_DIR%requirements.txt" (
    echo [75%%] Instalando dependencias do requirements.txt...
    "%BASE_DIR%\.venv\Scripts\python.exe" -m pip install -r "%BASE_DIR%requirements.txt"
) else (
    echo Nenhum requirements.txt encontrado.
)
echo.

REM --- Passo 4: Rodar Tp1_alt.py com Python da venv ---
if exist "%BASE_DIR%Tp1_alt.py" (
    echo [100%%] Executando Tp1_alt.py...
    "%BASE_DIR%\.venv\Scripts\python.exe" "%BASE_DIR%Tp1_alt.py"
) else (
    echo ERRO: Arquivo Tp1_alt.py nao encontrado na pasta do .bat.
)

REM --- Passo 5: Esperar 15 segundos e fechar ---
echo.
echo O script sera fechado.
timeout /t 0.1 /nobreak >nul
exit
