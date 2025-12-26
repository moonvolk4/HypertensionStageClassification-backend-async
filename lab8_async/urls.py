from django.urls import path
from app import views

urlpatterns = [
    path('calc', views.calc, name='calc'),
    path('calc/', views.calc, name='calc-slash'),
]
