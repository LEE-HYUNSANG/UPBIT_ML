from flask import Flask, render_template
from f1_universe import (
    select_universe,
    load_config,
    get_universe,
    schedule_universe_updates,
)

app = Flask(__name__)

CONFIG = load_config()
schedule_universe_updates(1800, CONFIG)

@app.route("/")
def home():
    """Root page showing the current trading universe."""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("index.html", universe=universe)


@app.route("/dashboard")
def dashboard():
    """Render the main dashboard page."""
    universe = get_universe()
    if not universe:
        universe = select_universe(CONFIG)
    return render_template("01_Home.html", universe=universe)


@app.route("/strategy")
def strategy():
    """Render the strategy configuration page."""
    return render_template("02_Strategy.html")


@app.route("/risk")
def risk():
    """Render the risk management page."""
    return render_template("03_Risk.html")


@app.route("/analysis")
def analysis():
    """Render the data analysis page."""
    return render_template("04_Analysis.html")


@app.route("/settings")
def settings():
    """Render the personal settings page."""
    return render_template("05_pSettings.html")


if __name__ == "__main__":
    # Run the Flask development server when executing this file directly.
    # Set host to "0.0.0.0" so the app is reachable via localhost.
    app.run(host="0.0.0.0", port=5000, debug=True)
