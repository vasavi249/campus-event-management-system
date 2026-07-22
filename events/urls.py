from django.urls import path
from . import views

urlpatterns = [
    # --- HTML Templates (Page routes) ---
    path('', views.home_view, name='home'),
    path('index.html', views.home_view, name='index_html_alias'),
    path('index/', views.home_view, name='index_alias'),
    path('events/', views.home_view, name='events_alias'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('login/', views.login_view, name='login_page'),
    path('register/', views.register_view, name='register_page'),
    
    # Dashboards
    path('dashboard/student/', views.student_dashboard_view, name='student_dashboard'),
    path('dashboard/student', views.student_dashboard_view, name='student_dashboard_alt'),
    path('dashboard/organizer/', views.organizer_dashboard_view, name='organizer_dashboard'),
    path('dashboard/organizer', views.organizer_dashboard_view, name='organizer_dashboard_alt'),
    path('dashboard/faculty/', views.faculty_dashboard_view, name='faculty_dashboard'),
    path('dashboard/faculty', views.faculty_dashboard_view, name='faculty_dashboard_alt'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/admin', views.admin_dashboard_view, name='admin_dashboard_alt'),

    
    # Events management
    path('event/<int:id>/', views.event_detail_view, name='event_detail_page'),
    path('event/create/', views.create_event_view, name='create_event_page'),
    path('event/<int:id>/edit/', views.edit_event_view, name='edit_event_page'),
    path('events/<int:id>/edit/', views.edit_event_view, name='edit_event_page_alias'),
    path('event/<int:id>/participants/', views.participant_list_view, name='participant_list_page'),
    path('event/<int:id>/attendance/', views.attendance_view, name='attendance_page'),
    
    # Student tools
    path('certificates/', views.certificates_view, name='certificates_page'),
    path('feedback/<int:id>/', views.feedback_view, name='feedback_page'),
    path('reports/', views.reports_view, name='reports_page'),
    path('profile/', views.profile_view, name='profile_page'),
    
    # --- REST API Endpoints ---
    # Auth APIs
    path('api/auth/register/', views.api_register, name='api_register'),
    path('users/add/', views.api_register, name='users_add_alias'),
    path('api/users/add/', views.api_register, name='api_users_add_alias'),
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),
    path('api/auth/forgot-password/', views.api_forgot_password, name='api_forgot_password'),
    path('api/auth/change-password/', views.api_change_password, name='api_change_password'),
    path('api/auth/profile/', views.api_profile, name='api_profile'),
    path('api/profile/update/', views.api_profile, name='api_profile_update'),
    
    # Venue APIs
    path('api/venues/', views.api_venues, name='api_venues'),
    path('api/venues/<int:pk>/', views.api_venue_detail, name='api_venue_detail'),

    # Events APIs
    path('api/events/', views.api_events, name='api_events'),
    path('api/events/<int:pk>/', views.api_event_detail, name='api_event_detail'),
    path('api/events/<int:pk>/approve/', views.api_event_approve, name='api_event_approve'),

    # Registration & Ticket Pass APIs
    path('api/registrations/', views.api_registrations, name='api_registrations'),
    path('api/registrations/<int:pk>/cancel/', views.api_registration_cancel, name='api_registration_cancel'),
    path('api/events/<int:pk>/registration/initiate/', views.api_initiate_registration, name='api_initiate_registration'),
    path('api/events/<int:pk>/registration/confirm/', views.api_confirm_registration, name='api_confirm_registration'),
    path('api/tickets/verify/', views.api_verify_ticket, name='api_verify_ticket'),

    # Attendance & Check-in APIs
    path('api/attendance/', views.api_attendance, name='api_attendance'),
    path('api/attendance/pending/', views.api_pending_department_attendance, name='api_pending_department_attendance'),
    path('api/attendance/<int:pk>/approve/', views.api_approve_attendance, name='api_approve_attendance'),
    path('api/attendance/<int:pk>/reject/', views.api_reject_attendance, name='api_reject_attendance'),
    path('api/attendance/checkin/', views.api_attendance_checkin, name='api_attendance_checkin'),

    # Faculty Specific Attendance Approvals APIs
    path('api/faculty/attendance-approvals/', views.api_faculty_attendance_approvals, name='api_faculty_attendance_approvals'),
    path('api/faculty/attendance-approvals/<int:pk>/approve/', views.api_faculty_approve_attendance, name='api_faculty_approve_attendance'),
    path('api/faculty/attendance-approvals/<int:pk>/reject/', views.api_faculty_reject_attendance, name='api_faculty_reject_attendance'),

    # Feedback & Certificate APIs
    path('api/feedback/', views.api_feedback, name='api_feedback'),
    path('api/certificates/', views.api_certificates, name='api_certificates'),
    path('api/certificates/<int:pk>/download/', views.api_download_certificate, name='api_download_certificate'),

    # Notification & Report APIs
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/reports/analytics/', views.api_dashboard_reports, name='api_dashboard_reports'),
    path('api/reports/csv/', views.api_export_report_csv, name='api_export_report_csv'),
    path('api/admin/users/', views.api_admin_manage_users, name='api_admin_manage_users'),
    path('api/admin/users/<int:pk>/', views.api_admin_manage_users, name='api_admin_manage_users_detail'),
]
