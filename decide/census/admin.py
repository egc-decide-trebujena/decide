
from django.contrib import admin

from .models import Census,CensusGroup
from import_export import resources
from import_export.admin import ImportExportModelAdmin



class CensusResource(resources.ModelResource):
    class Meta:
        model= Census


class CensusAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('voting_id', 'voter_id','group')
    list_filter = ('voting_id', 'group')
    raw_id_fields = ('group',)

    search_fields = ('voter_id', 'group')
    resource_class=CensusResource

class CensusGroupAdmin(admin.ModelAdmin):
    list_display = ('name','id')
    
    search_fields = ('name',)


admin.site.register(Census, CensusAdmin)
admin.site.register(CensusGroup, CensusGroupAdmin)
