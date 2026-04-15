from django.urls import path

from . import views

urlpatterns = [
    path("<str:dept_code>/handover/<str:date>/export.xlsx", views.export_handover_excel, name="export_handover_excel"),
    path("<str:dept_code>/handover/<str:date>/export.pdf", views.export_handover_pdf, name="export_handover_pdf"),
    path("<str:dept_code>/reports/", views.report_center, name="report_center"),
    path("<str:dept_code>/reports/export-range.xlsx", views.export_handover_range_excel, name="export_handover_range_excel"),
    path("<str:dept_code>/reports/export-range.pdf", views.export_handover_range_pdf, name="export_handover_range_pdf"),
]

