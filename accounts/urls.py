from django.urls import path

from . import views

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("switch-user/", views.switch_user, name="switch_user"),
]

