import os
import django
from datetime import date, time, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_event_manager.settings')
django.setup()

from django.contrib.auth import get_user_model
from events.models import Department, Category, Club, Venue, Event, Registration, Attendance, Feedback, Certificate, Notification

User = get_user_model()

def populate():
    print("--- Seeding Campus Event Management System Database ---")

    # 1. Departments
    dept_cs, _ = Department.objects.get_or_create(name="Computer Science & Engineering", code="CSE")
    dept_ece, _ = Department.objects.get_or_create(name="Electronics & Communication", code="ECE")
    dept_me, _ = Department.objects.get_or_create(name="Mechanical Engineering", code="ME")
    dept_mba, _ = Department.objects.get_or_create(name="Business Administration", code="MBA")

    # 2. Categories
    cat_tech, _ = Category.objects.get_or_create(name="Technical", description="Hackathons, coding contests, and tech symposiums")
    cat_cult, _ = Category.objects.get_or_create(name="Cultural", description="Music, dance, drama, and arts festivals")
    cat_work, _ = Category.objects.get_or_create(name="Workshop", description="Hands-on skill building & AI bootcamps")
    cat_sports, _ = Category.objects.get_or_create(name="Sports", description="Inter-department tournaments & athletics")

    # 3. Clubs
    club_coding, _ = Club.objects.get_or_create(name="Coding Club", description="Competitive programming & open source", department=dept_cs)
    club_robotics, _ = Club.objects.get_or_create(name="Robotics Society", description="Autonomous bots & hardware design", department=dept_ece)
    club_music, _ = Club.objects.get_or_create(name="Campus Music Society", description="Vocal & instrumental performances", department=dept_mba)

    # 4. Venues
    v1, _ = Venue.objects.get_or_create(venue_name="Main Seminar Hall A", building="Tech Block", capacity=150, has_projector=True, is_available=True)
    v2, _ = Venue.objects.get_or_create(venue_name="Auditorium Complex", building="Admin Block", capacity=500, has_projector=True, is_available=True)
    v3, _ = Venue.objects.get_or_create(venue_name="Computer Lab 3", building="CSE Annex", capacity=60, has_projector=True, is_available=True)

    # 5. Demo Users (One per role)
    admin_user, _ = User.objects.get_or_create(
        username="admin",
        defaults={
            'email': "admin@campus.edu",
            'first_name': "Global",
            'last_name': "Administrator",
            'role': "admin",
            'is_staff': True,
            'is_superuser': True
        }
    )
    admin_user.set_password("admin123")
    admin_user.save()

    vasavi_user, _ = User.objects.get_or_create(
        username="vasavi",
        defaults={
            'email': "vasavi@campus.edu",
            'first_name': "vasavi",
            'last_name': "latha",
            'role': "admin",
            'is_staff': True,
            'is_superuser': True
        }
    )
    vasavi_user.role = "admin"
    vasavi_user.is_staff = True
    vasavi_user.is_superuser = True
    vasavi_user.set_password("admin123")
    vasavi_user.save()

    faculty_user, _ = User.objects.get_or_create(
        username="faculty",
        defaults={
            'email': "faculty.cse@campus.edu",
            'first_name': "Prof. Alan",
            'last_name': "Turing",
            'role': "faculty",
            'department': dept_cs,
            'is_staff': True
        }
    )
    faculty_user.set_password("faculty123")
    faculty_user.save()

    organizer_user, _ = User.objects.get_or_create(
        username="organizer",
        defaults={
            'email': "coding.club@campus.edu",
            'first_name': "Grace",
            'last_name': "Hopper",
            'role': "organizer",
            'department': dept_cs,
            'club': club_coding
        }
    )
    organizer_user.set_password("organizer123")
    organizer_user.save()

    student_user, _ = User.objects.get_or_create(
        username="student",
        defaults={
            'email': "student.john@campus.edu",
            'first_name': "John",
            'last_name': "Doe",
            'role': "student",
            'roll_number': "CSE-2026-001",
            'department': dept_cs
        }
    )
    student_user.set_password("student123")
    student_user.save()

    # 6. Events
    event1, _ = Event.objects.get_or_create(
        title="Campus Hackathon 2026",
        defaults={
            'category': cat_tech,
            'description': "24-hour rapid prototyping hackathon focusing on AI agents and Web3 solutions.",
            'venue': v1,
            'date': timezone.now().date() + timedelta(days=7),
            'time': time(9, 30),
            'deadline': timezone.now() + timedelta(days=5),
            'max_participants': 100,
            'registration_fee': 250.00,
            'status': 'published',
            'approval_status': 'approved',
            'organizer': organizer_user,
            'department': dept_cs,
            'club': club_coding
        }
    )

    event2, _ = Event.objects.get_or_create(
        title="AI & Machine Learning Bootcamp",
        defaults={
            'category': cat_work,
            'description': "Hands-on neural network training workshop using PyTorch and HuggingFace models.",
            'venue': v3,
            'date': timezone.now().date() + timedelta(days=12),
            'time': time(14, 0),
            'deadline': timezone.now() + timedelta(days=10),
            'max_participants': 50,
            'registration_fee': 150.00,
            'status': 'published',
            'approval_status': 'approved',
            'organizer': organizer_user,
            'department': dept_cs,
            'club': club_coding
        }
    )

    event3, _ = Event.objects.get_or_create(
        title="Annual Cultural Gala Night",
        defaults={
            'category': cat_cult,
            'description': "Grand evening featuring live band performances, dance competitions, and theatrical drama.",
            'venue': v2,
            'date': timezone.now().date() + timedelta(days=15),
            'time': time(18, 0),
            'deadline': timezone.now() + timedelta(days=14),
            'max_participants': 400,
            'registration_fee': 100.00,
            'status': 'published',
            'approval_status': 'pending',
            'organizer': organizer_user,
            'department': dept_cs,
            'club': club_music
        }
    )

    event1.registration_fee = 250.00
    event1.save()

    event2.registration_fee = 150.00
    event2.save()

    event3.registration_fee = 100.00
    event3.approval_status = 'approved'
    event3.save()

    # 7. Registration & Digital Ticket Code
    reg, _ = Registration.objects.get_or_create(
        student=student_user,
        event=event1,
        defaults={
            'status': 'Confirmed',
            'attendance': 'present',
            'num_members': 2,
            'amount_paid': 500.00,
            'payment_status': 'paid',
            'payment_id': 'PAY-TXN-SEED123',
            'attendance_status': 'approved',
            'approved_by': faculty_user
        }
    )

    # 8. Attendance & Certificate
    Attendance.objects.get_or_create(
        registration=reg,
        defaults={'verified_by': faculty_user}
    )

    from events.utils import generate_certificate_pdf
    cert_path = generate_certificate_pdf(student_user, event1)
    Certificate.objects.get_or_create(
        student=student_user,
        event=event1,
        defaults={'certificate_file': cert_path}
    )

    # 9. Feedback
    Feedback.objects.get_or_create(
        student=student_user,
        event=event1,
        defaults={'rating': 5, 'comments': "Incredible event! Well structured and smooth ticket verification."}
    )

    # 10. Notification
    Notification.objects.get_or_create(
        user=student_user,
        title="Welcome to Campus Event Management Platform",
        defaults={'message': "Explore upcoming events, register with 1-click, and access your digital QR passes."}
    )

    print("--- Database Seeding Completed Successfully ---")

if __name__ == '__main__':
    populate()
