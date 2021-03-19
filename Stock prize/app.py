from flask import Flask, render_template, request
import sqlite3 as sql
from yahoo_fin import stock_info as si
import bs4 as bs
app = Flask(__name__)
# app.debug = True
connection = sql.connect("investments.db")
cursor = connection.cursor()
# cursor.execute("CREATE TABLE investments(serialnumber INTEGER PRIMARY KEY,date DATE, symbol TEXT,name TEXT,quantity int, bought_prize decimal(20,2),current_prize decimal(20,2))")

import os
from datetime import date
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import pandas_datareader 
import datetime
import io
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas_datareader.data as web

@app.route('/sell/<id>/<price>',methods=['POST'])
def sell(id,price):
    if 'sell' in request.form:
        conn = sql.connect("investments.db")
        cur = conn.cursor()
        info=cur.execute("SELECT * FROM investments WHERE serialnumber = :id", {"id": id}).fetchall()[0]
        quantt=request.form['quantity']
        data=int(info[4])-int(quantt)
        lst=[data,id]
        print(lst)
        if int(quantt) < int(info[4]):
            cur.execute("""UPDATE investments SET quantity= ? WHERE serialnumber= ?""",lst)
        elif int(quantt) == int(info[4]):
            cur.execute("DELETE FROM investments WHERE serialnumber = :id", {"id": id})
        conn.commit()
        conn.close()
        connection=sql.connect("returns.db")
        db=connection.cursor()
        today=date.today()
        date1=today.strftime("%d-%m-%Y")
        change=(float(price)-float(info[5]))/float(price)
        # db.execute("DELETE FROM returns")
        # db.execute("CREATE TABLE returns(serialnumber INTEGER PRIMARY KEY,buy_date DATE,sell_date, symbol TEXT,name TEXT,quantity int, bought_price decimal(20,2),sell_price decimal(20,2),change FLOAT)")
        db.execute("INSERT INTO returns(serialnumber ,buy_date,sell_date, symbol,name,quantity, bought_price,sell_price,change ) VALUES (NULL,?,?,?,?,?,?,?,?)",(info[1],date1,info[2],info[3],quantt,round(info[5],2),price,round(change*100,2)))
        connection.commit()
        connection.close()
        return id
        
    else:
        return "nameerror!"

@app.route('/returns', methods = ['POST','GET'])
def returns():
    try:
        conn = sql.connect("returns.db")
        conn.row_factory = sql.Row
        cur = conn.cursor()
        cur.execute("select * from returns")
        msg = cur.fetchall()
        lst=cur.execute("SELECT bought_price,sell_price,quantity FROM returns").fetchall()
        profit=sum(list((b-a)*c for a,b,c in lst)) 
        if profit>=0:
            message="Net Profit"
        else:
            message="Net Loss"
        return render_template("returns.html",msg = msg,profit=round(profit),message=message)
    
    except:
        return "error in returns"


@app.route('/<sym>', methods = ['POST','GET'])
def details(sym):
        data = sym
        end   = datetime.datetime.today()
        start = datetime.datetime(end.year-2, 1, 1)
        prize=si.get_live_price(data)
        fig = Figure()
        delta = web.DataReader(data, 'yahoo', start,end)
        fig = plt.figure()
        delta['Adj Close'].plot(figsize = (15,8), grid=True)
        pngImage = io.BytesIO()
        FigureCanvas(fig).print_png(pngImage)
        pngImageB64String = "data:image/png;base64,"
        pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
        return render_template("result.html", image=pngImageB64String,msg=prize, symbol=data)

@app.route('/buy/<symbol>', methods = ['POST'])        
def buy(symbol):
    if 'buy' in request.form:
        try:
            def buysym(symbol):
                    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(symbol)
                    import requests
                    result = requests.get(url).json()
                    for x in result['ResultSet']['Result']:
                        if x['symbol'] == symbol:
                            return x['name']            
            connection = sql.connect("investments.db")
            cursor = connection.cursor()
            today=date.today()
            date1=today.strftime("%d-%m-%Y")
            company = buysym(symbol)
            quantity=request.form['quantity']
            bought_prize=si.get_live_price(symbol)
            current_prize=si.get_live_price(symbol)
            change=((current_prize-bought_prize)/current_prize)*100

            cursor.execute("INSERT INTO investments(date, symbol,name,quantity, bought_prize,current_prize ) VALUES (?,?,?,?,?,?)",(date1,symbol,company,quantity,bought_prize,current_prize))
            # cursor.execute("INSERT INTO invest(serialnumber ,date, symbol,name,quantity, bought_prize ) VALUES ('1',?,?,?,?,?)",(date1,symbol,company,quantity,bought_prize))
            # cursor.execute("UPDATE stock SET species= 'ACC.NS' WHERE id = '6'")
            # cursor.execute("DELETE FROM investments")
            connection.commit()
            msg="record added successfully."

        except:
            connection.rollback()
            msg = "error in insert operation"

        finally:
            return "done!"
            connection.close()
        # return render_template("buy.html",msg=msg,date=date1,symbol=symbol,company=company,quantity=pay,bought_prize=bought_prize)
    else:
        return "nameerror!"

@app.route('/investments')
def invest():
    try:
        conn = sql.connect("investments.db")
        conn.row_factory = sql.Row
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM investments")
        symbols=cur.fetchall()
        cur.execute("SELECT serialnumber FROM investments")
        s=cur.fetchall()
        s1=[v[0] for v in s]
        val=tuple(round(si.get_live_price(symbol[0]),2) for symbol in symbols)
        key=tuple(value for value in s1)
        lst=[(k,v) for (k,v) in dict(zip(key,val)).items()]
        l=[tup[::-1] for tup in lst]
        cur.executemany("""UPDATE investments SET current_prize= ? WHERE serialnumber= ?""",l)
        cur.execute("select * from investments")
        msg = cur.fetchall()

        cur.execute("SELECT quantity FROM investments")
        q=cur.fetchall()
        quantity=[a[0] for a in q]
        cur.execute("SELECT bought_prize FROM investments")
        bp=cur.fetchall()
        bought_price=[b[0] for b in bp]
        lst=[k*v for (k,v) in dict(zip(quantity,bought_price)).items()]
        TI=round(sum(lst),2)

        cur.execute("SELECT current_prize FROM investments")
        cp=cur.fetchall()
        current_price=[c[0] for c in cp]
        lst1=[k*v for (k,v) in dict(zip(quantity,current_price)).items()]
        CP=round(sum(lst1),2)
        return render_template("buy.html",msg = msg,TI=TI,CP=CP)
    
    except:
        print("error in investment")


@app.route('/')
def example():
    try:
        connection = sql.connect("data.db")
        cursor = connection.cursor()
        # cursor.execute("INSERT INTO stock VALUES ('1','Amazon','AMZN')")
        # cursor.execute("INSERT INTO stock VALUES ('3','TCS', 'TCS')")
        # cursor.execute("INSERT INTO stock VALUES ('2','Apple','AAPL')")
        # cursor.execute("INSERT INTO stock VALUES ('6','ACC ltd.','ACC.NS')")
        # cursor.execute("INSERT INTO stock VALUES ('4','Union Bank','UNB')")
        # cursor.execute("UPDATE stock SET species= 'SBIN.NS' WHERE id = '5'")
        # cursor.execute("UPDATE stock SET species= 'ACC.NS' WHERE id = '6'")
        # cursor.execute("DELETE FROM stocks")
        connection.commit()
        msg="record added successfully."

    except:
         connection.rollback()
         msg = "error in insert operation"

    finally:
        return render_template("result.html",msg = msg)
        # print(msg)
        connection.close()

@app.route('/data')
def data():
   conn = sql.connect("data.db")
   conn.row_factory = sql.Row
   cur = conn.cursor()
   cur.execute("select * from stock")
   rows = cur.fetchall()
   return render_template("home.html",rows = rows)

if __name__ == '__main__':
   app.run(debug = True)