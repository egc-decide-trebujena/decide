from django.urls import path, include
from . import views

app_name="census"

urlpatterns = [
    path('', views.CensusCreate.as_view(), name='census_create'),
    path('<int:voting_id>/', views.CensusDetail.as_view(), name='census_detail'),
    path('new/', views.census_creation2, name='census_creation2'),
    path('export/', views.export_excel,name="export_excel"),
    path('censusgroups/',views.CensusGroupCreate.as_view(), name='census_group_list'),
    path('censusgroups/<int:pk>/',views.CensusGroupDetail.as_view(), name='census_group_detail'),
    
]
