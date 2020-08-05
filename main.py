from odoo import Odoo
import json
import base64
from PIL import Image
from io import BytesIO
from datetime import datetime


#Establecer Parámetros
##################################################################
conn = Odoo(db="universal",login="admin",password="Odoo",
            url="localhost:8005",ssl=False)
##################################################################



conn.authenticate()
error_logs = open("error_logs_{}.logs".format(datetime.now().strftime("%Y-%m-%d %H-%M-%S")),"w")

def fetch_products(conn):
    res = conn.call_kw("product.template","search_read",[],{"domain":[],"fields":["id"]})
    return list(map(lambda r:r["id"],res))

def download_product_image(conn,product_id):
    res = conn.call_kw("product.template","search_read",[],{"domain":[["id","=",product_id]],"fields":["name","image"]})
    if len(res)>0:
        image_id = res[0]["id"]
        image_b64 = res[0]["image"]
        try:
            im = Image.open(BytesIO(base64.b64decode(image_b64)))
            im.save('images/{}.png'.format(image_id), 'PNG')
        except Exception as e:
            error_logs.write("Product id:{}, error:{}\n".format(image_id,e))
        

    
products = fetch_products(conn)
for i,product_id in enumerate(products):
    download_product_image(conn,product_id)
    print(i,product_id)

# download_product_image(conn,33561)