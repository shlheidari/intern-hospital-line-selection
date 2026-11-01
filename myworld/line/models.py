from django.db import models
from preventconcurrentlogins.models import Visitor as BaseVisitor

class UserImportJob(models.Model):
    import_file = models.FileField(upload_to='data/imports/user/')
    status = models.CharField(max_length=20, default='Pending', 
               choices=[('Pending', 'Pending'), ('Processing', 'Processing'),
                        ('Completed', 'Completed'), ('Failed', 'Failed')])
    result = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Import Job {self.id} - {self.status}"


class VisitorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('user')

class Visitor(BaseVisitor):
    objects = VisitorManager()
    
    class Meta:
        proxy = True
    
    @classmethod
    def enforce_single_visitor(cls, user):
        """Ensure only one visitor exists per user"""
        visitors = cls.objects.filter(user=user)
        if visitors.count() > 1:
            # Keep the first one (or use some other logic)
            visitors.exclude(pk=visitors.first().pk).delete()

class Members(models.Model):
    id = models.AutoField(primary_key=True)
    num = models.IntegerField()
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=255,null=True)
    logged = models.BooleanField(default=False)
    first = models.BooleanField(default=False)
    last = models.BooleanField(default=False)
    student_id = models.CharField(max_length=255)
    start_time = models.CharField(max_length=255)
    end_time = models.CharField(max_length=255)
    line = models.CharField(max_length=255,null=True)
    surgery = models.CharField(max_length=255,null=True)
    internal = models.CharField(max_length=255,null=True)
    pediatrics = models.CharField(max_length=255,null=True)
    gynocology = models.CharField(max_length=255,null=True)
    emergency = models.CharField(max_length=255,null=True)
    elective_one = models.CharField(max_length=255,null=True)
    elective_two = models.CharField(max_length=255,null=True)
    elective_three = models.CharField(max_length=255,null=True)
    orthopedix = models.CharField(max_length=255,null=True)
    cardiology = models.CharField(max_length=255,null=True)

    class Meta:
        db_table = 'line_members'

    def __str__(self):
        return f'{self.num}. {self.name}'

class Capacity(models.Model):
    id = models.AutoField(primary_key=True)
    gender = models.CharField(max_length=255,null=True)
    line = models.CharField(max_length=255)
    unit = models.CharField(max_length=255)
    hospital = models.CharField(max_length=255)
    full = models.IntegerField()
    reserved = models.IntegerField()
    remain = models.IntegerField()
    common = models.CharField(max_length=255,null=True)

    class Meta:
        db_table = 'line_capacity'

    def __str__(self):
        return f'{self.unit} / {self.hospital} ({self.remain}/{self.full})'

class Selection(models.Model):
    id = models.AutoField(primary_key=True)
    item_fa = models.CharField(max_length=255)
    item_en = models.CharField(max_length=255)
    choice = models.CharField(max_length=255)
    iden = models.CharField(max_length=255)
    line_c = models.CharField(max_length=255)

    class Meta:
        db_table = 'line_selection'

    def __str__(self):
        return f'{self.item_fa}: {self.choice}'

class Shared(models.Model):
    id = models.AutoField(primary_key=True)
    unit = models.CharField(max_length=255)
    shared_unit = models.CharField(max_length=255)

    class Meta:
        db_table = 'line_shared'

    def __str__(self):
        return f'{self.unit} -> {self.shared_unit}'
