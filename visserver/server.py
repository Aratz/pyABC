from flask import Flask, render_template
from flask_bootstrap import Bootstrap
import sys
import bokeh.plotting.helpers as helpers
helpers.DEFAULT_PALETTE = ['#000000',   # Wong nature colorblind palette
                            '#e69f00',
                            '#56b4e9',
                            '#009e73',
                            '#f0e442',
                            '#0072b2',
                            '#d55e00',
                            '#cc79a7']
from bokeh.charts import Line, Scatter, Bar
from bokeh.embed import components
import os
import json
from pyabc import History
from bokeh.resources import INLINE
import pandas as pd
from bokeh.models.widgets import Panel, Tabs
BOKEH = INLINE



class PlotScriptDiv:
    def __init__(self, script, div):
        self.script=script
        self.div = div


app = Flask(__name__)
Bootstrap(app)


@app.route('/')
def main():
    return render_template("index.html")


@app.route("/abc")
def abc_overview():
    runs = history.all_runs()
    return render_template("abc_overview.html", runs=runs)


class ABCInfo:
    def __init__(self, abc):
        self.abc = abc

    def __getattr__(self, item):
        json_str = getattr(self.abc, item).replace("'", '"')
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return json_str


@app.route("/abc/<int:abc_id>")
def abc_detail(abc_id):
    history.id = abc_id
    abc = ABCInfo(history.this_abc())
    model_probabilities = history.get_model_probabilities()
    model_ids = model_probabilities.columns
    model_probabilities.columns = list(map(lambda x: "{}".format(x),
                                           model_probabilities.columns))
    model_probabilities = model_probabilities.reset_index()
    if len(model_probabilities) > 0:
        populations = history.get_all_populations()
        populations = populations[populations.t > 0]
        particles = (history.get_nr_particles_per_population().reset_index()
                     .rename(columns={"index": "t", "t": "particles"}).query("t > 0"))

        melted = pd.melt(model_probabilities, id_vars="t", var_name="m", value_name="p")
        prob_plot = Bar(melted, label="t", stack="m", values="p")
        prob_plot.ylabel = "p"
        plot = Tabs(tabs=[Panel(child=prob_plot, title="Probability"),
                          Panel(child=Scatter(x="t", y="nr_samples", data=populations), title="Samples"),
                          Panel(child=Scatter(x="t", y="particles", data=particles), title="Particles"),
                          Panel(child=Scatter(x="t", y="epsilon", data=populations), title="Epsilon")])
        plot = PlotScriptDiv(*components(plot))
        return render_template("abc_detail.html",
                               abc_id=abc_id,
                               plot=plot,
                               BOKEH=BOKEH,
                               model_ids=model_ids,
                               abc=abc)
    return render_template("abc_detail.html",
                           abc_id=abc_id,
                           plot=PlotScriptDiv("", "Exception: No data found."),
                           BOKEH=BOKEH,
                           abc=abc)


@app.route("/abc/<int:abc_id>/model/<int:model_id>/t/<t>")
def abc_model(abc_id, model_id, t):
    history.id = abc_id
    if t == "max":
        t = history.max_t
    else:
        t = int(t)
    df, w = history.weighted_parameters_dataframe(t, model_id)
    df["CDF"] = w
    tabs = []
    for parameter in [col for col in df if col != "CDF"]:
        plot_df = df[["CDF", parameter]].sort_values(parameter)
        plot_df_cumsum = plot_df.cumsum()
        plot_df_cumsum[parameter] = plot_df[parameter]
        p = Panel(child=Line(x=parameter, y="CDF", data=plot_df_cumsum), title=parameter)
        tabs.append(p)
    if len(tabs) == 0:
        plot = PlotScriptDiv("", "This model has no Parameters")
    else:
        plot = PlotScriptDiv(*components(Tabs(tabs=tabs)))
    return render_template("model.html",
                           abc_id=abc_id,
                           model_id=model_id,
                           plot=plot,
                           BOKEH=BOKEH,
                           t=t,
                           available_t=list(range(history.max_t+1)))


@app.route("/info")
def server_info():
    return render_template("server_info.html", db_path=history.db_path, db_size=round(history.db_size, 2))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


db = os.path.expanduser(sys.argv[1])
history = History("sqlite:///" + db)


def run_app():
    app.run(debug=True)


if __name__ == '__main__':
    run_app()