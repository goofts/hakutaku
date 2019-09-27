from peewee import Model, PrimaryKeyField, CharField, DateTimeField
from playhouse.pool import PooledSqliteDatabase as sqlite
from playhouse.shortcuts import ReconnectMixin as rcmx
from pathlib import Path

class RetrySqLiteDatabase(rcmx, sqlite):
    _instance = None
 
    @staticmethod
    def get_sqlite_instance():
        if not RetrySqLiteDatabase._instance:
            RetrySqLiteDatabase._instance = RetrySqLiteDatabase(
                str(Path(str(Path(__file__).parent.parent)) / Path('sqlitedb') / Path('github')),
                max_connections=8
            )
        return RetrySqLiteDatabase._instance

db: sqlite = RetrySqLiteDatabase.get_sqlite_instance()

class BaseModel(Model):
    class Meta:
        database = db

class GITHUB(BaseModel):
    id      = PrimaryKeyField()
    unique  = CharField(verbose_name='序号', null=False, unique=True)
    url     = DateTimeField(verbose_name='链接', null=False)
    name    = CharField(verbose_name='规则名', null=False)
    keyword = CharField(verbose_name='关键词', null=False)
    count   = CharField(verbose_name='匹配次数', null=False)

    class Meta:
        order_by = ('id',)
        db_table = 'github'