#!/bin/bash

echo "Iniciando setup del entorno SmartBite..."
echo ""

# Verificacion de Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker no esta instalado"
    exit 1
fi

# Verificacion de Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "[ERROR] Docker Compose no esta instalado"
    exit 1
fi

# Verificacion de que el dataset este en el directorio
if [ ! -f "dataset.csv" ]; then
    echo "[ERROR] No se encontro dataset.csv"
    echo "Por favor coloca el archivo dataset.csv en el directorio del proyecto"
    exit 1
fi

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "No se encontro archivo .env, creando uno con valores por defecto..."
    cat > .env << EOF
# Variables de entorno del proyecto
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=v2
POSTGRES_HOST=db
POSTGRES_PORT=5432
FLASK_ENV=development
FLASK_APP=app.py
EOF
    echo "Archivo .env creado."
else
    echo "Archivo .env ya existe."
fi

echo ""
echo "Construyendo contenedores e iniciando servicios..."
echo ""
echo "Algunas Consideraciones:"
echo "- La primera vez puede tardar varios minutos"
echo "- La carga del dataset para poblar la base de datos puede tardar 10-15 minutos"
echo "- Se puede ver el progreso con: docker-compose logs -f web"
echo ""

docker-compose up --build -d

echo "Esperando a que los contenedores arranquen..."
sleep 10

echo ""
echo "Estado de los contenedores:"
docker-compose ps
echo ""

echo "Esperando que el servicio web este disponible..."
RETRIES=0
MAX_RETRIES=10

while [ $RETRIES -lt $MAX_RETRIES ]; do
    # Se verifica si la app web esta respondiendo
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo ""
        echo "SmartBite esta corriendo en: http://localhost:5000"
        exit 0
    fi
    
    RETRIES=$((RETRIES + 1))
    sleep 2
done

echo "No se pudo verificar que la app este corriendo todavia."
echo "Revisa los logs con: docker-compose logs -f web"
echo ""