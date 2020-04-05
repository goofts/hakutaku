from app    import DB_FILE
from peewee import SqliteDatabase, sqlite3
from peewee import Model
from peewee import PrimaryKeyField
from peewee import CharField, DateTimeField
from playhouse.pool      import PooledDatabase
from playhouse.shortcuts import ReconnectMixin as rcmx

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
                DB_FILE,
                max_connections=8
            )
        return RetrySqliteDatabase._instance

DB: sqlite = RetrySqliteDatabase.get_sqlite_instance()

class BaseModel(Model):
    class Meta:
        database = DB

class repository(BaseModel):
    id      = PrimaryKeyField()
    unique  = CharField(verbose_name='哈希值', null=False, unique=True)
    url     = DateTimeField(verbose_name='链接', null=False)
    name    = CharField(verbose_name='规则名', null=False)
    keyword = CharField(verbose_name='关键词', null=False)
    count   = CharField(verbose_name='匹配次数', null=False)

    class Meta:
        order_by = ('id',)
        db_table = 'repository'

class hashlist(BaseModel):
    id      = PrimaryKeyField()
    unique  = CharField(verbose_name='哈希值', null=False, unique=True)

    class Meta:
        order_by = ('id',)
        db_table = 'hashlist'
