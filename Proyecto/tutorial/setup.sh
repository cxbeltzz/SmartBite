#!/bin/bash
set -e

echo -e "Iniciando setup del entorno SmartBite..."

# Verificacion de Docker
if ! command -v docker &> /dev/null; then
  echo -e "Docker no está instalado"
  exit 1
fi

# Verificacion de Docker Compose
if ! command -v docker-compose &> /dev/null; then
  echo -e "Docker Compose no está instalado."
  exit 1
fi

# Creacion del archivo .env si no existe
if [ ! -f ".env" ]; then
  echo -e "No se encontro archivo .env, creando uno con valores por defecto..."
  cat > .env <<EOF

# Variables de entorno del proyecto
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=TUTORIAL
POSTGRES_HOST=db
POSTGRES_PORT=5432
FLASK_ENV=development
FLASK_APP=app.py
EOF
  echo -e "Archivo .env creado."
else
  echo -e "Archivo .env ya existe."
fi

# Levantar los servicios
echo -e "Construyendo contenedores e iniciando servicios..."
docker-compose up --build -d

# Toca esperar unos segundos para asegurar que los contenedores arranquen
sleep 5

# Mostrar estado
echo -e "Estado de los contenedores:"
docker-compose ps

# Se verifica si la app web responde
echo -e "Esperando que el servicio web este disponible..."
for i in {1..10}; do
  if curl -s http://localhost:5000 >/dev/null; then
    echo -e "SmartBite esta corriendo en: http://localhost:5000"
    exit 0
  fi
  sleep 2
done

echo -e "No se pudo verificar que la app este corriendo todavia."
echo "Revisa los logs con: docker-compose logs -f web"
