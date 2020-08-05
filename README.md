Crear entorno Virtual
$ virtualenv -p python env

Uso de entorno virtual
$ . env/bin/activate

instalar dependencias
$ pip install -r requirements.txt

Establecer parámetros en script main.py

conn = Odoo(db="universal",login="admin",password="Odoo",url="localhost:8005",ssl=False)

Ejecutar script:
$ python main.py