@echo off
setlocal enabledelayedexpansion
echo  Iniciando setup del entorno SmartBite...


REM Verificacion de Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker no esta instalado
    pause
    exit /b 1
)

REM Verificacion de Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose no esta instalado
    pause
    exit /b 1
)

REM Crear archivo .env si no existe
if not exist ".env" (
    echo No se encontro archivo .env, creando uno con valores por defecto...
    (
        echo # Variables de entorno del proyecto
        echo POSTGRES_USER=postgres
        echo POSTGRES_PASSWORD=password
        echo POSTGRES_DB=TUTORIAL
        echo POSTGRES_HOST=db
        echo POSTGRES_PORT=5432
        echo FLASK_ENV=development
        echo FLASK_APP=app.py
    ) > .env
    echo Archivo .env creado.
) else (
    echo Archivo .env ya existe.
)

echo.
echo Construyendo contenedores e iniciando servicios...
docker-compose up --build -d

echo Esperando a que los contenedores arranquen...
timeout /t 10 >nul

echo.
echo Estado de los contenedores:
docker-compose ps
echo.

echo Esperando que el servicio web este disponible...
set RETRIES=0
:check_loop
set /a RETRIES+=1
if !RETRIES! gtr 10 goto not_ready

# Se verifica si la app web responde
curl -s http://localhost:5000 >nul 2>&1
if %errorlevel%==0 (
    echo.
    echo SmartBite esta corriendo en: http://localhost:5000
    goto end
)

timeout /t 2 >nul
goto check_loop

:not_ready
echo No se pudo verificar que la app este corriendo todavia.
echo Revisa los logs con: docker-compose logs -f web

:end
echo.
pause
