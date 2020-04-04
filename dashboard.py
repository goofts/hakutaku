import os
import sys
import traceback
import asyncio
import dash, dash_table, pandas
import dash_core_components as dcc
import dash_html_components as html
from pathlib  import Path
from datetime import datetime
from peewee   import Model, PrimaryKeyField, CharField, DateTimeField
from app      import gsil
from dash.dependencies   import Input, Output
from playhouse.pool      import PooledSqliteDatabase as sqlite
from playhouse.shortcuts import ReconnectMixin as rcmx
from gsil.notification   import Notification
from apscheduler.schedulers.asyncio import AsyncIOScheduler


dbpath: str = str(Path(self.APP_PATH) / Path('sqlitedb'))
if not os.path.exists(dbpath):
    os.mkdir(dbpath)

dbfile: str = str(Path(dbpath) / Path('{0}.sqlite3'.format(self.DATABASE_NAME)))

try:
    from peewee import SqliteDatabase, sqlite3
    from playhouse.pool import PooledDatabase
    from playhouse.shortcuts import ReconnectMixin as rcmx
except:
    print ('please run "pip3 install -r requirements" to install packages first')
    sys.exit(-1)

class Sqlite3Database(SqliteDatabase):
    def _connect(self):
        if sqlite3 is None:
            raise ImproperlyConfigured('SQLite driver not installed!')

        conn = sqlite3.connect(
            self.database,
            timeout=self._timeout,
            isolation_level=None,
            check_same_thread=False,
            **self.connect_params
        )

        try:
            self._add_conn_hooks(conn)
        except:
            conn.close()
            raise
        return conn

class _sqlite(PooledDatabase):
    def _is_closed(self, conn):
    try:
        conn.total_changes
    except:
        return True
        else:
    return False

class sqlite(_sqlite, Sqlite3Database):
    pass

class RetrySqliteDatabase(rcmx, sqlite):
    _instance = None

    @staticmethod
    def get_sqlite_instance():
    if not RetrySqliteDatabase._instance:
        RetrySqliteDatabase._instance = RetrySqliteDatabase(
            dbfile,
            max_connections=self.MAX_CONNECTIONS_LENGTH
        )
    return RetrySqliteDatabase._instance

db: sqlite = RetrySqliteDatabase.get_sqlite_instance()

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
    try:
        scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        scheduler.add_job(gsil, 'cron', hour="*/2")
        scheduler.start()
        app.run_server(debug=True, host='0.0.0.0', port=8000)
    except Exception as e:
        content = '{a}\r\n{e}'.format(a=' '.join(sys.argv), e=traceback.format_exc())
        Notification('GSIL Exception').notification(content)
