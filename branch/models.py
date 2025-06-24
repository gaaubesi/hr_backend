from django.db import models

# Create your models here.
class Branch(models.Model):
    name = models.CharField(unique=True, max_length=50)
    code = models.CharField(unique=True, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'

class Province(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    cbs_code = models.IntegerField(null=True, blank=True)

class District(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    cbs_code = models.IntegerField(null=True, blank=True)
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    province = models.ForeignKey(
        "Province", related_name="districts", on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.name)