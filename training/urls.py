from django.urls import path

from . import views

urlpatterns = [
    path("<str:dept_code>/courses/", views.course_list, name="course_list"),
    path("<str:dept_code>/courses/<int:course_id>/", views.course_detail, name="course_detail"),
    path("<str:dept_code>/courses/<int:course_id>/qr.png", views.course_qr, name="course_qr"),
    path("<str:dept_code>/courses/manage/", views.course_manage_list, name="course_manage_list"),
    path("<str:dept_code>/courses/manage/new/", views.course_create, name="course_create"),
    path("<str:dept_code>/courses/manage/<int:course_id>/edit/", views.course_edit, name="course_edit"),
    path("<str:dept_code>/courses/manage/<int:course_id>/delete/", views.course_delete, name="course_delete"),
    path("<str:dept_code>/courses/manage/upload-image/", views.course_upload_image, name="course_upload_image"),
    path("<str:dept_code>/courses/manage/media/", views.media_library_page, name="media_library_page"),
    path("<str:dept_code>/courses/manage/media/api/", views.media_assets_api, name="media_assets_api"),
    path("<str:dept_code>/courses/manage/media/<int:asset_id>/delete/", views.media_asset_delete, name="media_asset_delete"),
]

