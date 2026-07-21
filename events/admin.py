from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Department, Club, Category, Venue, CustomUser, Event, Registration, Attendance, Feedback, Certificate, Notification

admin.site.site_header = "Campus Event Management Admin Portal"
admin.site.site_title = "Campus Events Admin"
admin.site.index_title = "Manage Events, Banners, Users & Approvals"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'roll_number')
    list_filter = ('role', 'department')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'roll_number')
    fieldsets = UserAdmin.fieldsets + (
        ('Campus Identity Role Details', {'fields': ('role', 'phone', 'roll_number', 'department', 'club')}),
    )

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date', 'time', 'venue', 'registration_fee', 'status', 'approval_status', 'organizer', 'banner_preview', 'certificate_template_preview')
    list_filter = ('category', 'status', 'approval_status', 'date')
    search_fields = ('title', 'description', 'organizer__username')
    readonly_fields = ('event_id', 'banner_preview', 'certificate_template_preview')

    def banner_preview(self, obj):
        if obj.banner_image:
            return format_html('<img src="{}" style="height: 50px; border-radius: 6px; object-fit: cover;" />', obj.banner_image.url)
        return format_html('<span style="color: #999;">No Poster</span>')
    banner_preview.short_description = "Banner Preview"

    def certificate_template_preview(self, obj):
        if obj.certificate_template:
            return format_html('<img src="{}" style="height: 50px; border-radius: 6px; object-fit: cover;" />', obj.certificate_template.url)
        return format_html('<span style="color: #999;">Default Gold Template</span>')
    certificate_template_preview.short_description = "Certificate Template"

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'student', 'event', 'num_members', 'amount_paid', 'payment_status', 'attendance_status', 'approved_by')
    list_filter = ('payment_status', 'attendance_status', 'event')
    search_fields = ('ticket_code', 'student__username', 'payment_id')

admin.site.register(Department)
admin.site.register(Club)
admin.site.register(Category)
admin.site.register(Venue)
admin.site.register(Attendance)
admin.site.register(Feedback)
admin.site.register(Certificate)
admin.site.register(Notification)
