from django.urls import path
from . import views

app_name = "hr"

urlpatterns = [
    # إنشاء وبحث
    path("applicants/new/", views.applicant_create, name="applicant_create"),
    path("applicants/search/", views.applicant_search_or_create, name="applicant_search_or_create"),

    # قائمة/تفاصيل/تعديل/حذف/قرار
    path("applicants/", views.applicant_list, name="applicant_list"),
    path("applicants/<int:order_number>/", views.applicant_detail, name="applicant_detail"),
    path("applicants/<int:order_number>/edit/", views.applicant_edit, name="applicant_edit"),
    path("applicants/<int:order_number>/delete/", views.applicant_delete, name="applicant_delete"),
    path("applicants/<int:order_number>/decision/", views.applicant_decision, name="applicant_decision"),

    # المقبولون / المحذوفات
    path("accepted/", views.accepted_list, name="accepted_list"),
    path("deleted/", views.deleted_list, name="deleted_list"),

    # الدور
    path("queue/", views.queue_view, name="queue_view"),
    path("queue/next/", views.queue_next, name="queue_next"),
    path("queue/prev/", views.queue_prev, name="queue_prev"),
    # تصدير إكسل
    path("export/applicant/<int:order_number>/", views.export_applicant_excel, name="export_applicant_excel"),
    path("export/applicants/", views.export_applicants_excel, name="export_applicants_excel"),

    path("dashboard/", views.hr_dashboard, name="hr_dashboard"),
    path("help-dashboard/", views.hr_help_dashboard, name="hr_help_dashboard"),

]
