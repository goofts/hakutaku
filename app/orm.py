from app import DB

class BaseModel(Model):
    class Meta:
        database = DB

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
