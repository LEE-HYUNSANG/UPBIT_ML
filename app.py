from flask import Flask, render_template
from f1_universe import select_universe

app = Flask(__name__)

@app.route("/")
def home():
    tickers = select_universe()
    return render_template("index.html", tickers=tickers)
