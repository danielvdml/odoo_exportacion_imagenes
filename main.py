from odoo import Odoo
import json
import base64
from PIL import Image
from io import BytesIO
from datetime import datetime
import pandas as pd

#Establecer Parámetros
##################################################################
conn = Odoo(db="universal",login="admin",password="Odoo",
            url="localhost:8005",ssl=False)
##################################################################

conn.authenticate()


def fetch_product_ids(conn):
    res = conn.call_kw("product.template","search_read",[],{"domain":[],"fields":["id"]})
    return list(map(lambda r:r["id"],res))

def download_product_image(conn,product_id):
    error_logs = open("error_logs_{}.logs".format(datetime.now().strftime("%Y-%m-%d %H-%M-%S")),"w")
    res = conn.call_kw("product.template","search_read",[],{"domain":[["id","=",product_id]],"fields":["name","image"]})
    if len(res)>0:
        image_id = res[0]["id"]
        image_b64 = res[0]["image"]
        try:
            im = Image.open(BytesIO(base64.b64decode(image_b64)))
            im.save('images/{}.png'.format(image_id), 'PNG')
        except Exception as e:
            error_logs.write("Product id:{}, error:{}\n".format(image_id,e))
        


def transform(r):
    r_clone = r
    for d in r.keys():
        if type(r[d]) == list:
            r_clone[d] = r[d][1]    
        
    return r_clone

def fetch_producs(conn,fields):
    res = conn.call_kw("product.template","search_read",[],{"domain":[],"fields":fields})
    res = map(lambda r:transform(r),res)
    df = pd.DataFrame(res,columns=fields)
    df.to_excel("products.xlsx","Productos")




def download_images():
    products = fetch_product_ids(conn)
    for i,product_id in enumerate(products):
        download_product_image(conn,product_id)
        print(i,product_id)


#Descarga en excel de los productos con campos: ---
#fetch_producs(conn,["id","name","type","list_price","standard_price","categ_id"])
#Descarga de imágenes
#download_images()
