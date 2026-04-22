from django.urls import path

from . import views

urlpatterns = [
    path("<str:dept_code>/", views.m_home, name="m_home"),
    path("<str:dept_code>/handover/today/", views.handover_today, name="handover_today"),
    path("<str:dept_code>/handover/history/", views.handover_history, name="handover_history"),
    path("<str:dept_code>/handover/today/fill/", views.handover_fill_today, name="handover_fill_today"),
    path(
        "<str:dept_code>/handover/today/fill/<str:section>/",
        views.handover_fill_section_today,
        name="handover_fill_section_today",
    ),
    path(
        "<str:dept_code>/handover/today/fill/items/new/",
        views.handover_fill_item_create_today,
        name="handover_fill_item_create_today",
    ),
    path(
        "<str:dept_code>/handover/today/fill/items/<int:item_id>/edit/",
        views.handover_fill_item_edit_today,
        name="handover_fill_item_edit_today",
    ),
    path(
        "<str:dept_code>/handover/today/fill/items/<int:item_id>/delete/",
        views.handover_fill_item_delete_today,
        name="handover_fill_item_delete_today",
    ),
    path("<str:dept_code>/handover/qr.png", views.handover_today_qr, name="handover_today_qr"),
    path("<str:dept_code>/handover/<str:date>/", views.handover_by_date, name="handover_by_date"),
    path("<str:dept_code>/handover/<str:date>/fill/", views.handover_fill_by_date, name="handover_fill_by_date"),
    path(
        "<str:dept_code>/handover/<str:date>/fill/<str:section>/",
        views.handover_fill_section_by_date,
        name="handover_fill_section_by_date",
    ),
    path(
        "<str:dept_code>/handover/<str:date>/fill/items/new/",
        views.handover_fill_item_create_by_date,
        name="handover_fill_item_create_by_date",
    ),
    path(
        "<str:dept_code>/handover/<str:date>/fill/items/<int:item_id>/edit/",
        views.handover_fill_item_edit_by_date,
        name="handover_fill_item_edit_by_date",
    ),
    path(
        "<str:dept_code>/handover/<str:date>/fill/items/<int:item_id>/delete/",
        views.handover_fill_item_delete_by_date,
        name="handover_fill_item_delete_by_date",
    ),
]

