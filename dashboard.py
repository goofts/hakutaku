import sys
import traceback
import dash, dash_table, pandas
import dash_core_components as dcc
import dash_html_components as html
from pathlib  import Path
from datetime import datetime
from peewee   import Model, PrimaryKeyField, CharField, DateTimeField
from gsil     import gsil
from dash.dependencies   import Input, Output
from playhouse.pool      import PooledSqliteDatabase as sqlite
from playhouse.shortcuts import ReconnectMixin as rcmx
from gsil.notification   import Notification

class RetrySqLiteDatabase(rcmx, sqlite):
    _instance = None
 
    @staticmethod
    def get_sqlite_instance():
        if not RetrySqLiteDatabase._instance:
            RetrySqLiteDatabase._instance = RetrySqLiteDatabase(
                str(Path(str(Path(__file__).parent)) / Path('sqlitedb') / Path('github')),
                max_connections=8
            )
        return RetrySqLiteDatabase._instance

db: sqlite = RetrySqLiteDatabase.get_sqlite_instance()

app = dash.Dash(__name__)

now = datetime.now()

app.layout = html.Div([
    html.H1('敏感信息'),
    html.Div([
        html.Div([
            dcc.Interval(id='iss_table_interval', interval=5 * 60 * 1000, n_intervals=0),
            dash_table.DataTable(
                id='iss_table',
                columns=[
                    {'name': '规则名', 'id': '规则名', "renamable": True},
                    {'name': '关键词', 'id': '关键词', "renamable": True},
                    {'name': '匹配次数', 'id': '匹配次数', "renamable": True},
                    {'name': '链接', 'id': '链接', "renamable": True}
                ],
                style_cell_conditional=[
                    {
                        'if': {'column_id': column},
                        'textAlign': 'left'
                    } for column in ['规则名', '关键词', '匹配次数', '链接']
                ],
                style_cell={'padding': '5px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                column_selectable="single",
                page_action="native",
                page_current= 0,
                page_size= 10,
                export_format='xlsx',
                export_headers='display',
                merge_duplicate_headers=True,
                css=[
                    {"selector": ".column-header--delete svg", "rule": 'display: "none"'},
                    {"selector": ".column-header--delete::before", "rule": 'content: "X"'}
                ]
            ),
        ], 
        className="table"),
    ], className="tender_announcement"),
])

@app.callback(
    Output('iss_table', 'data'),
    [
        Input('iss_table_interval', 'n_intervals')
    ]
)
def search_ta_for_release(intervals):
    sql = "select name as '规则名', keyword as '关键词', count as '匹配次数', url as '链接' from github;"
    ta_data = pandas.read_sql(sql, db)
    db.close()
    return ta_data.to_dict('records')

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8000)
