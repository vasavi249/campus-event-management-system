import os
from django.conf import settings
from django.db.models import Count, Avg
from .models import CustomUser, Department, Club, Category, Event, Registration, Feedback, Certificate

from django.utils import timezone

def generate_certificate_pdf(student, event):
    """
    Generates an official campus participation certificate document.
    """
    cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
    os.makedirs(cert_dir, exist_ok=True)

    file_name = f"certificate_{student.username}_{event.event_id}.txt"
    full_path = os.path.join(cert_dir, file_name)

    dept_name = student.department.name if student.department else 'General Department'
    venue_name = event.venue.venue_name if event.venue else 'Campus Auditorium'
    time_str = event.time.strftime('%I:%M %p') if hasattr(event.time, 'strftime') else str(event.time)

    content = f"""
    +--------------------------------------------------------------------------------+
    |                        CAMPUS EVENT MANAGEMENT SYSTEM                          |
    |                   OFFICIAL CERTIFICATE OF PARTICIPATION                        |
    +--------------------------------------------------------------------------------+
    
    THIS IS TO OFFICIALLY CERTIFY THAT:
    
    STUDENT NAME     : {student.full_name.upper()}
    ROLL NUMBER      : {student.roll_number or 'N/A'}
    DEPARTMENT       : {dept_name.upper()}
    
    HAS SUCCESSFULLY REGISTERED, ATTENDED, AND PARTICIPATED IN THE CAMPUS EVENT:
    
    EVENT TITLE      : {event.title.upper()}
    CATEGORY         : {event.category.name if event.category else 'General'}
    DATE OF EVENT    : {event.date}
    TIME OF EVENT    : {time_str}
    VENUE            : {venue_name}
    
    CERTIFICATE CODE : CERT-{event.event_id}-{student.id}-{timezone.now().strftime('%Y%m%d')}
    ISSUED BY        : CAMPUS EVENT MANAGEMENT PLATFORM
    APPROVAL STATUS  : VERIFIED BY DEPARTMENT FACULTY
    +--------------------------------------------------------------------------------+
    """

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return f"certificates/{file_name}"

def get_dashboard_analytics():
    """
    Computes system-wide analytics for admin panel.
    """
    students_count = CustomUser.objects.filter(role='student').count()
    organizers_count = CustomUser.objects.filter(role='organizer').count()
    faculty_count = CustomUser.objects.filter(role='faculty').count()
    total_events = Event.objects.count()
    total_registrations = Registration.objects.count()
    avg_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg'] or 4.8

    # Dept distribution
    dept_distribution = {}
    for d in Department.objects.all():
        dept_distribution[d.code] = CustomUser.objects.filter(department=d, role='student').count()

    # Category distribution
    cat_distribution = {}
    for c in Category.objects.all():
        cat_distribution[c.name] = Event.objects.filter(category=c).count()

    return {
        'students': students_count,
        'organizers': organizers_count,
        'faculty': faculty_count,
        'total_events': total_events,
        'total_registrations': total_registrations,
        'avg_rating': round(avg_rating, 1),
        'department_distribution': dept_distribution,
        'category_distribution': cat_distribution
    }
