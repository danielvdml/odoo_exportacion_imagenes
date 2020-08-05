import requests 
import json
from datetime import datetime
import threading
import time
import sys

class Odoo:
    def __init__(self,db=None,login=None,password=None,url=None,ssl=False,session=""):
        self.db = db
        self.login = login
        self.password = password
        self.session = session
        self.ssl = ssl
        self.url = url
        
    def authenticate(self):
        data = {    
            "jsonrpc":"2.0",    
            "method":"call",    
            "params":{        
                "db":self.db,        
                "login":self.login,        
                "password":self.password   
            }
        }
        headers = {
            "Content-Type":"application/json",
            "Accept":"application/json",
            'Connection': "keep-alive",
        }
        #response = requests.request("POST","{}://{}/web/session/authenticate".format("https" if self.ssl else "http",self.url),data=json.dumps(data),headers=headers)
        s = requests.Session()
        req = requests.Request("POST",
                "{}://{}/web/session/authenticate".format("https" if self.ssl else "http",self.url),
                data=json.dumps(data),
                headers=headers)
        prepped = req.prepare()
        response = s.send(prepped)
        if response.status_code == 200:
            res = response.json()
            self.session = res["result"]["session_id"]

    def get_session_info(self):
        data = {    
            "jsonrpc":"2.0",    
            "method":"call",    
            "params":{ 
            }
        }
        headers = {
            "Accept":"application/json",
            "Content-Type":"application/json",
            "Host":self.url
        }
        response = requests.request("POST","{}://{}/web/session/get_session_info".format("https" if self.ssl else "http",self.url),cookies={"session_id":str(self.session)})
        #print(response.text)
        if response.status_code == 200:
            res = response.json()
            self.session = res["result"]["session_id"]
            #print(self.session)

    def call_kw(self,model,method,args=[],kwargs={},version=11):
        if not self.session:
            return False
        data = {    
            "jsonrpc":"2.0",    
            "method":"call",    
            "params":{
                "model":model,
                "method":method,   
                "args":args,
                "kwargs":kwargs
            }
        }
        headers = {
            "Content-Type":"application/json",
            "Accept":"application/json",
            "Cookie":"session_id={}".format(self.session)
        }
        if version == 12:
            response = requests.request("POST","{}://{}/web/dataset/call_kw/{}/{}".format("https" if self.ssl else "http",self.url,model,method),data=json.dumps(data),headers=headers,cookies={"session_id":str(self.session)})
        else:
            response = requests.request("POST","{}://{}/web/dataset/call_kw".format("https" if self.ssl else "http",self.url),data=json.dumps(data),headers=headers,cookies={"session_id":str(self.session)})
        if response.status_code == 200:
            res = response.json()
            if "result" in res:
                return res["result"]
            else:
                print(res)
                pass
        return []
    
    def download_json(self,model,fields,limit=10,order=False,transform=None,domain=None,path=False,version=11):
        now = datetime.now().strftime("%Y%m%d")
        kwargs = {"fields":fields}
        if limit>0:
            kwargs.update({"limit":limit})
        if order:
            kwargs.update({"order":order})
        if domain:
            kwargs.update({"domain":domain})

        records = self.call_kw(model,"search_read",[],kwargs,version=version)
        if path:
            path = path if path[-1] == "/" else path+"/"
        file_json = "{}{}_download_{}.json".format(path if path else "",model,now)
        
        data_json = open(file_json,"w",encoding="latin-1")
        for record in records:
            for field in record:
                if type(record[field]) == list and len(record[field]) == 2:
                    if type(record[field][0]) == int  and type(record[field][1]) == str:
                        record[field] = record[field][0]
                    else:
                        record[field] = [(6,0,record[field])]
                elif type(record[field]) == list:
                    record[field] = [(6,0,record[field])]
        if transform:
            records = transform(records)
        data = {
            "metadata":{
                "length":len(records),
                "model":model,
                "fields":fields
            },
            "data":records
        }
        data_json.write(json.dumps(data,indent=4))
        data_json.close()
        return file_json

    def load_json(self,model,file_json,dup=False,
                        transform=None,
                        version=11,
                        threads=1,
                        field_active=False,
                        field_company=False,
                        field_code=False,
                        field_login=False,
                        field_name=False):
        data_file_json = open(file_json,"r")
        data_text = data_file_json.read()
        load = json.loads(data_text)
        if not load.get("data"):
            return ""
        else:
            records = load.get("data")

        data_load_json = {}
        now = datetime.now().strftime("%Y%m%d")
        file_load_json = open("{}_load_{}.json".format(model,now),"w",encoding="latin-1")
        file_load_json_logs = open("{}_load_{}_logs.json".format(model,now),"w",encoding="latin-1")
        
        def worker(records,name,idx):
            total = len(records)
            for idx,record in enumerate(records):
                #print(name,":",idx,"/",total)
                sys.stdout.write("\r{}: {}/{}".format(name,idx,total,"\n"*idx))
                sys.stdout.flush()
                if record.get("parent_id",False):
                    try:
                        record["parent_id"] = data_load_json[record["parent_id"]]["id"]
                    except Exception as e:
                        record["parent_id"]
                if transform:
                    record = transform(record,records=data_load_json)

                if record.get("write",False):
                    old_id = record["id"]
                    new_id = record["new_id"]
                    record["id"] = new_id
                    del record["new_id"]
                    del record["write"]
                    record["active"] = True
                    print("write",record)
                    self.call_kw(model,"write",[[new_id],record])
                    data_load_json[old_id] = record
                elif dup:
                    if field_code:
                        domain = [["code","=",record["code"]]]
                    elif field_login:
                        domain = [["login","=",record["login"]]]

                    if field_name:
                        domain = [["name","=",record["name"]]]

                    if field_company:
                        domain += [["company_id","=",record["company_id"]]]
                    if field_active:
                        domain = ['|',["active","=",0],["active","=",1]] + domain
                        
                    print(domain)
                    rec = self.call_kw(model,"search_read",[],kwargs={"domain":domain},version=version)
                    
                    old_id = record["id"]
                    if len(rec)==0:
                        res_new_id = self.call_kw(model,"create",[record],{},version=version)
                        if res_new_id:
                            record_new = record
                            record_new["id"] = res_new_id
                            data_load_json[old_id] = record_new
                        else:
                            file_load_json_logs.write(json.dumps(record,indent=4))
                    else:
                        record["id"] = rec[0]["id"]
                        #self.call_kw(model,"write",[[record["id"]],record])
                        data_load_json[old_id] = record
                else:
                    if not record.get("write",False):
                        old_id = record["id"]
                        del record["id"]
                        res_new_id = self.call_kw(model,"create",[record],{},version=version)
                        if res_new_id:
                            record_new = record
                            record_new["id"] = res_new_id
                            data_load_json[old_id] = record_new
                        else:
                            file_load_json_logs.write(json.dumps(record,indent=4))
                    else:
                        old_id = record["id"]
                        new_id = record["new_id"]
                        record["id"] = new_id
                        del record["new_id"]
                        del record["write"]
                        self.call_kw(model,"write",[[new_id],record])
                        data_load_json[old_id] = record

        l_threads = []
        for idx,t_records in enumerate([records[i:i+int(len(records)/threads)] for i in range(0,len(records),int(len(records)/threads))]):
            t = threading.Thread(target=worker,args=(t_records,"thread {}".format(idx),idx))
            l_threads.append(t)
            t.start()
        ex = True
        
        c = sum([int(t.isAlive()) for t in l_threads])
        while  c > 0:
            c = sum([int(t.isAlive()) for t in l_threads])
    
        file_load_json.write(json.dumps(data_load_json,indent=4))
        file_load_json.close()

    