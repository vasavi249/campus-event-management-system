import os
import csv
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import (
    Department, Category, Club, Venue, CustomUser, Event,
    Registration, Attendance, Feedback, Certificate, Notification
)
from .serializers import (
    DepartmentSerializer, CategorySerializer, ClubSerializer, VenueSerializer,
    CustomUserSerializer, EventSerializer, RegistrationSerializer, AttendanceSerializer,
    FeedbackSerializer, CertificateSerializer, NotificationSerializer
)
from .utils import generate_certificate_pdf, get_dashboard_analytics

User = get_user_model()

# Helper for standardized REST API JSON responses
def api_response(status_str, message, data=None, http_status=status.HTTP_200_OK):
    return Response({
        'status': status_str,
        'message': message,
        'data': data
    }, status=http_status)

from django.http import HttpResponse, JsonResponse, Http404

def safe_get_object_or_404(klass, *args, **kwargs):
    """
    Safely retrieves an object or raises Http404, catching ValueError/TypeError 
    if invalid IDs (e.g. empty strings, nulls, non-integers) are supplied to integer fields.
    """
    try:
        for k, v in list(kwargs.items()):
            if k in ['pk', 'id', 'event_id', 'venue_id', 'department_id', 'club_id', 'registration_id', 'certificate_id']:
                if v is None or (isinstance(v, str) and not v.strip().isdigit()):
                    raise Http404(f"Invalid primary key for {klass.__name__}.")
        return get_object_or_404(klass, *args, **kwargs)
    except (ValueError, TypeError, DjangoValidationError):
        raise Http404(f"Object not found in {klass.__name__}.")

from django.views.static import serve as django_serve

def safe_media_serve(request, path):
    """
    Safely serves uploaded media files directly from MEDIA_ROOT.
    If requested file does not exist on disk, serves sample_proof.png fallback image.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return django_serve(request, path, document_root=settings.MEDIA_ROOT)
    
    fallback_path = os.path.join(settings.MEDIA_ROOT, 'payment_screenshots', 'sample_proof.png')
    if os.path.exists(fallback_path) and os.path.isfile(fallback_path):
        return django_serve(request, 'payment_screenshots/sample_proof.png', document_root=settings.MEDIA_ROOT)
    
    return HttpResponse("Payment screenshot file not found.", status=404)

# Custom 404 View
def custom_404_view(request, exception=None):
    if request.path.startswith('/api/'):
        return JsonResponse({
            'status': 'error',
            'message': 'Resource not found',
            'data': None
        }, status=404)
    return render(request, 'events/404.html', status=404)


# =========================================================================
# FRONTEND TEMPLATE VIEWS (Page Routing)
# =========================================================================

def home_view(request):
    events = Event.objects.filter(status='published', approval_status='approved').order_by('date')
    categories = Category.objects.all()
    return render(request, 'events/home.html', {
        'categories': categories,
        'events': events,
        'total_events': events.count(),
        'total_students': User.objects.filter(role='student').count()
    })

def about_view(request):
    return render(request, 'events/about.html')

def contact_view(request):
    return render(request, 'events/contact.html')

def redirect_user_to_dashboard(user):
    if user.is_superuser or user.role == 'admin':
        return redirect('admin_dashboard')
    elif user.role == 'faculty':
        return redirect('faculty_dashboard')
    elif user.role == 'organizer':
        return redirect('organizer_dashboard')
    return redirect('student_dashboard')

def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_to_dashboard(request.user)
    return render(request, 'events/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect_user_to_dashboard(request.user)
    departments = Department.objects.all()
    clubs = Club.objects.all()
    return render(request, 'events/register.html', {
        'departments': departments,
        'clubs': clubs
    })

@login_required
def student_dashboard_view(request):
    try:
        role = (getattr(request.user, 'role', '') or 'student').lower().strip()
        if role == 'faculty':
            return redirect('faculty_dashboard')
        elif role == 'organizer':
            return redirect('organizer_dashboard')
        elif role == 'admin' or request.user.is_superuser:
            return redirect('admin_dashboard')

        user = request.user
        registrations = Registration.objects.filter(student=user).select_related('event')
        certificates = Certificate.objects.filter(student=user).select_related('event')
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
        categories = Category.objects.filter(events__status='published', events__approval_status='approved').distinct()
        upcoming_events = Event.objects.filter(status='published', approval_status='approved').order_by('date')
    except Exception:
        registrations = Registration.objects.none()
        certificates = Certificate.objects.none()
        notifications = Notification.objects.none()
        categories = Category.objects.none()
        upcoming_events = Event.objects.none()

    return render(request, 'events/student_dashboard.html', {
        'registrations': registrations,
        'certificates': certificates,
        'notifications': notifications,
        'categories': categories,
        'upcoming_events': upcoming_events
    })

@login_required
def organizer_dashboard_view(request):
    try:
        role = (getattr(request.user, 'role', '') or 'student').lower().strip()
        if role == 'student':
            return redirect('student_dashboard')
        elif role == 'faculty':
            return redirect('faculty_dashboard')

        events = Event.objects.filter(organizer=request.user).order_by('-date')
        venues = Venue.objects.filter(is_available=True)
        categories = Category.objects.all()
    except Exception:
        events = Event.objects.none()
        venues = Venue.objects.none()
        categories = Category.objects.none()

    return render(request, 'events/organizer_dashboard.html', {
        'events': events,
        'venues': venues,
        'categories': categories
    })

@login_required
def faculty_dashboard_view(request):
    try:
        role = (getattr(request.user, 'role', '') or 'student').lower().strip()
        if role == 'student':
            return redirect('student_dashboard')
        elif role == 'organizer':
            return redirect('organizer_dashboard')

        dept = getattr(request.user, 'department', None)
        if dept:
            pending_events = Event.objects.filter(
                Q(department=dept) | Q(department__isnull=True),
                approval_status='pending'
            ).order_by('date')
        else:
            pending_events = Event.objects.filter(approval_status='pending').order_by('date')

        approved_events = Event.objects.filter(approval_status='approved').order_by('date')
    except Exception:
        pending_events = Event.objects.none()
        approved_events = Event.objects.none()

    return render(request, 'events/faculty_dashboard.html', {
        'pending_events': pending_events,
        'approved_events': approved_events
    })

@login_required
def admin_dashboard_view(request):
    try:
        role = (getattr(request.user, 'role', '') or 'student').lower().strip()
        if role not in ['admin'] and not request.user.is_superuser:
            if role == 'faculty':
                return redirect('faculty_dashboard')
            elif role == 'organizer':
                return redirect('organizer_dashboard')
            return redirect('student_dashboard')

        analytics = get_dashboard_analytics()
        users = User.objects.all().order_by('-date_joined')[:10]
        events = Event.objects.all().order_by('-date')[:10]
        departments = Department.objects.all()
        clubs = Club.objects.all()
        categories = Category.objects.all()
        venues = Venue.objects.filter(is_available=True)
    except Exception:
        analytics = {'total_students': 0, 'total_organizers': 0, 'total_faculty': 0, 'total_events': 0, 'total_registrations': 0}
        users = User.objects.none()
        events = Event.objects.none()
        departments = Department.objects.none()
        clubs = Club.objects.none()
        categories = Category.objects.none()
        venues = Venue.objects.none()

    return render(request, 'events/admin_dashboard.html', {
        'analytics': analytics,
        'recent_users': users,
        'recent_events': events,
        'departments': departments,
        'clubs': clubs,
        'categories': categories,
        'venues': venues
    })

def event_detail_view(request, id):
    event = safe_get_object_or_404(Event, pk=id)
    is_registered = False
    student_reg = None
    if request.user.is_authenticated and request.user.role == 'student':
        student_reg = Registration.objects.filter(student=request.user, event=event).first()
        is_registered = bool(student_reg)
        
    feedbacks = event.feedbacks.all()
    avg_rating = feedbacks.aggregate(Avg('rating'))['rating__avg'] or 0.0
    
    return render(request, 'events/event_detail.html', {
        'event': event,
        'is_registered': is_registered,
        'student_reg': student_reg,
        'feedbacks': feedbacks,
        'avg_rating': round(avg_rating, 1)
    })

@login_required
def create_event_view(request):
    if request.user.role not in ['organizer', 'admin'] and not request.user.is_superuser:
        return redirect('home')
        
    categories = Category.objects.all()
    venues = Venue.objects.filter(is_available=True)
    departments = Department.objects.all()
    clubs = Club.objects.all()
    
    return render(request, 'events/create_event.html', {
        'categories': categories,
        'venues': venues,
        'departments': departments,
        'clubs': clubs
    })

@login_required
def edit_event_view(request, id):
    event = safe_get_object_or_404(Event, pk=id)
    if request.user != event.organizer and request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')
        
    categories = Category.objects.all()
    venues = Venue.objects.all()
    departments = Department.objects.all()
    return render(request, 'events/edit_event.html', {
        'event': event,
        'categories': categories,
        'venues': venues,
        'departments': departments
    })

@login_required
def participant_list_view(request, id):
    event = safe_get_object_or_404(Event, pk=id)
    if request.user != event.organizer and request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return redirect('home')
        
    registrations = event.registrations.all()
    return render(request, 'events/participant_list.html', {
        'event': event,
        'registrations': registrations
    })

@login_required
def attendance_view(request, id):
    event = safe_get_object_or_404(Event, pk=id)
    if request.user != event.organizer and request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return redirect('home')
        
    registrations = event.registrations.filter(status='Confirmed')
    return render(request, 'events/attendance.html', {
        'event': event,
        'registrations': registrations
    })

@login_required
def certificates_view(request):
    certificates = Certificate.objects.filter(student=request.user)
    return render(request, 'events/certificates.html', {'certificates': certificates})

@login_required
def feedback_view(request, id):
    event = safe_get_object_or_404(Event, pk=id)
    existing_feedback = Feedback.objects.filter(student=request.user, event=event).first()
    return render(request, 'events/feedback.html', {
        'event': event,
        'feedback': existing_feedback
    })

@login_required
def reports_view(request):
    if request.user.role not in ['organizer', 'faculty', 'admin'] and not request.user.is_superuser:
        return redirect('home')
        
    analytics = get_dashboard_analytics()
    events = Event.objects.all()
    return render(request, 'events/reports.html', {
        'analytics': analytics,
        'events': events
    })

@login_required
def profile_view(request):
    departments = Department.objects.all()
    clubs = Club.objects.all()
    return render(request, 'events/profile.html', {
        'departments': departments,
        'clubs': clubs
    })


# =========================================================================
# REST API ENDPOINTS (Separation of Concerns)
# =========================================================================

# --- AUTH API ---

@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role', 'student')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    phone = request.data.get('phone', '')
    roll_number = request.data.get('roll_number', '')
    dept_id = request.data.get('department')
    club_id = request.data.get('club')

    if not username or not email or not password:
        return api_response('error', 'Username, email, and password are required.', http_status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username__iexact=username.strip()).exists():
        return api_response('error', f"Username '{username}' is already taken. Please choose another username.", http_status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email__iexact=email.strip()).exists():
        return api_response('error', f"Email '{email}' is already registered.", http_status=status.HTTP_400_BAD_REQUEST)

    if roll_number and User.objects.filter(roll_number__iexact=roll_number.strip()).exists():
        return api_response('error', f"Roll number '{roll_number}' is already registered to another student.", http_status=status.HTTP_400_BAD_REQUEST)

    dept = None
    if dept_id:
        try:
            dept = Department.objects.get(pk=dept_id)
        except (Department.DoesNotExist, ValueError):
            return api_response('error', 'Selected department does not exist.', http_status=status.HTTP_400_BAD_REQUEST)

    club = None
    if club_id:
        try:
            club = Club.objects.get(pk=club_id)
        except (Club.DoesNotExist, ValueError):
            return api_response('error', 'Selected club does not exist.', http_status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.create_user(
            username=username.strip(),
            email=email.strip(),
            password=password,
            role=role,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone.strip() if phone else None,
            roll_number=roll_number.strip() if roll_number else None,
            department=dept,
            club=club
        )

        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        serializer = CustomUserSerializer(user)
        
        return api_response('success', 'User registered successfully.', {
            'token': token.key,
            'user': serializer.data
        }, http_status=status.HTTP_201_CREATED)
    except Exception as e:
        return api_response('error', f"Registration error: {str(e)}", http_status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return api_response('error', 'Username and password required.', http_status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return api_response('error', 'Invalid username or password.', http_status=status.HTTP_401_UNAUTHORIZED)

    if user.role == 'admin' and (not user.is_staff or not user.is_superuser):
        user.is_staff = True
        user.is_superuser = True
        user.save()

    login(request, user)
    token, _ = Token.objects.get_or_create(user=user)
    serializer = CustomUserSerializer(user)

    return api_response('success', 'Login successful.', {
        'token': token.key,
        'user': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    logout(request)
    return api_response('success', 'Logged out successfully.')


@api_view(['POST'])
@permission_classes([AllowAny])
def api_forgot_password(request):
    email = request.data.get('email')
    if email:
        user = User.objects.filter(email__iexact=email.strip()).first()
        if user:
            return api_response('success', f"Password reset instructions sent to {email}.")
    return api_response('error', 'Email address not found.', http_status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_change_password(request):
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not request.user.check_password(old_password):
        return api_response('error', 'Current password is incorrect.', http_status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(new_password)
    request.user.save()
    return api_response('success', 'Password changed successfully.')


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_profile(request):
    user = request.user
    if request.method == 'GET':
        serializer = CustomUserSerializer(user)
        return api_response('success', 'Profile retrieved.', serializer.data)

    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    phone = request.data.get('phone')
    roll_number = request.data.get('roll_number')
    dept_id = request.data.get('department')
    club_id = request.data.get('club')
    new_password = request.data.get('new_password')

    if first_name is not None:
        user.first_name = first_name.strip()
    if last_name is not None:
        user.last_name = last_name.strip()
    if email:
        if User.objects.filter(email__iexact=email.strip()).exclude(pk=user.pk).exists():
            return api_response('error', 'Email is already registered by another account.', http_status=status.HTTP_400_BAD_REQUEST)
        user.email = email.strip()

    if phone is not None:
        user.phone = phone.strip()

    if roll_number is not None:
        if roll_number.strip() and User.objects.filter(roll_number__iexact=roll_number.strip()).exclude(pk=user.pk).exists():
            return api_response('error', 'Roll number is already registered to another user.', http_status=status.HTTP_400_BAD_REQUEST)
        user.roll_number = roll_number.strip() if roll_number.strip() else None

    if dept_id:
        try:
            user.department = Department.objects.get(pk=dept_id)
        except (Department.DoesNotExist, ValueError):
            pass

    if club_id:
        try:
            user.club = Club.objects.get(pk=club_id)
        except (Club.DoesNotExist, ValueError):
            pass

    if new_password and len(new_password.strip()) >= 6:
        user.set_password(new_password.strip())

    user.save()

    serializer = CustomUserSerializer(user)
    return api_response('success', 'Profile updated successfully!', serializer.data)


# --- VENUES API ---

@api_view(['GET', 'POST'])
def api_venues(request):
    if request.method == 'GET':
        venues = Venue.objects.all()
        serializer = VenueSerializer(venues, many=True)
        return api_response('success', 'Venues list retrieved.', serializer.data)

    if not request.user.is_authenticated or request.user.role not in ['admin', 'organizer']:
        return api_response('error', 'Unauthorized permission.', http_status=status.HTTP_403_FORBIDDEN)

    serializer = VenueSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return api_response('success', 'Venue created successfully.', serializer.data, http_status=status.HTTP_201_CREATED)
    return api_response('error', 'Invalid venue data.', serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_venue_detail(request, pk):
    venue = safe_get_object_or_404(Venue, pk=pk)

    if request.method == 'GET':
        serializer = VenueSerializer(venue)
        return api_response('success', 'Venue detail retrieved.', serializer.data)

    if not request.user.is_authenticated or request.user.role != 'admin':
        return api_response('error', 'Admin permission required.', http_status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = VenueSerializer(venue, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Venue updated successfully.', serializer.data)
        return api_response('error', 'Invalid data.', serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)

    venue.delete()
    return api_response('success', 'Venue deleted successfully.')


# --- EVENTS API ---

@api_view(['GET', 'POST'])
def api_events(request):
    if request.method == 'GET':
        events = Event.objects.all()

        search_query = request.query_params.get('search')
        category_id = request.query_params.get('category')
        status_param = request.query_params.get('status')
        approval_param = request.query_params.get('approval_status')

        if search_query:
            events = events.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
        if category_id:
            if category_id.isdigit():
                events = events.filter(category_id=category_id)
            else:
                events = events.filter(category__name__iexact=category_id)
        if status_param:
            events = events.filter(status=status_param)
        if approval_param:
            events = events.filter(approval_status=approval_param)

        serializer = EventSerializer(events, many=True, context={'request': request})
        return api_response('success', 'Events retrieved.', serializer.data)

    if not request.user.is_authenticated or request.user.role not in ['organizer', 'admin']:
        return api_response('error', 'Only organizers and admins can create events.', http_status=status.HTTP_403_FORBIDDEN)

    try:
        data = {k: v for k, v in request.data.items()}
        data['organizer'] = request.user.id
        dept_val = request.data.get('department')
        if dept_val:
            data['department'] = dept_val
        elif getattr(request.user, 'department_id', None):
            data['department'] = request.user.department_id

        if getattr(request.user, 'club_id', None):
            data['club'] = request.user.club_id

        for folder in ['event_banners', 'certificate_templates', 'certificates', 'payment_scanners', 'payment_screenshots']:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, folder), exist_ok=True)

        if 'banner_image' in request.FILES:
            data['banner_image'] = request.FILES['banner_image']
        elif 'banner_image' in data and not hasattr(data['banner_image'], 'read'):
            del data['banner_image']

        if 'certificate_template' in request.FILES:
            data['certificate_template'] = request.FILES['certificate_template']
        elif 'certificate_template' in data and not hasattr(data['certificate_template'], 'read'):
            del data['certificate_template']

        if 'payment_scanner' in request.FILES:
            data['payment_scanner'] = request.FILES['payment_scanner']
        elif 'payment_scanner' in data and not hasattr(data['payment_scanner'], 'read'):
            del data['payment_scanner']

        serializer = EventSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            try:
                event = serializer.save()
            except DjangoValidationError as ve:
                err_msg = str(ve.message_dict if hasattr(ve, 'message_dict') else ve)
                return api_response('error', err_msg, http_status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return api_response('error', f"Could not save event: {str(e)}", http_status=status.HTTP_400_BAD_REQUEST)

            # Notify Faculty safely
            try:
                faculties = User.objects.filter(role='faculty')
                for fac in faculties:
                    Notification.objects.create(
                        user=fac,
                        title="New Event Submitted for Approval",
                        message=f"Event '{event.title}' created by {request.user.username} requires your review."
                    )
            except Exception:
                pass

            return api_response('success', 'Event created successfully and submitted for faculty approval.', serializer.data, http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation error while creating event.', serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)

    except Exception as general_err:
        import traceback
        traceback.print_exc()
        return api_response('error', f"Server error while creating event: {str(general_err)}", http_status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def api_event_detail(request, pk):
    event = safe_get_object_or_404(Event, pk=pk)

    if request.method == 'GET':
        serializer = EventSerializer(event, context={'request': request})
        return api_response('success', 'Event detail retrieved.', serializer.data)

    if not request.user.is_authenticated or (request.user != event.organizer and request.user.role != 'admin'):
        return api_response('error', 'Unauthorized to modify this event.', http_status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        data = {k: v for k, v in request.data.items()}
        if request.data.get('remove_banner') == 'true' or request.data.get('remove_banner') is True:
            if event.banner_image:
                event.banner_image.delete(save=False)
                event.banner_image = None
                event.save()

        if request.data.get('remove_certificate_template') == 'true' or request.data.get('remove_certificate_template') is True:
            if event.certificate_template:
                event.certificate_template.delete(save=False)
                event.certificate_template = None
                event.save()

        if request.data.get('remove_payment_scanner') == 'true' or request.data.get('remove_payment_scanner') is True:
            if event.payment_scanner:
                event.payment_scanner.delete(save=False)
                event.payment_scanner = None
                event.save()

        if 'banner_image' in request.FILES:
            data['banner_image'] = request.FILES['banner_image']
        elif 'banner_image' in data and not hasattr(data['banner_image'], 'read'):
            del data['banner_image']

        if 'certificate_template' in request.FILES:
            data['certificate_template'] = request.FILES['certificate_template']
        elif 'certificate_template' in data and not hasattr(data['certificate_template'], 'read'):
            del data['certificate_template']

        if 'payment_scanner' in request.FILES:
            data['payment_scanner'] = request.FILES['payment_scanner']
        elif 'payment_scanner' in data and not hasattr(data['payment_scanner'], 'read'):
            del data['payment_scanner']

        serializer = EventSerializer(event, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            updated_event = serializer.save()

            # Notify registered students of update
            regs = Registration.objects.filter(event=updated_event, status='Confirmed')
            for r in regs:
                Notification.objects.create(
                    user=r.student,
                    title="Event Update Notice",
                    message=f"Details for event '{updated_event.title}' have been updated by the organizer."
                )

            return api_response('success', 'Event updated successfully.', serializer.data)
        return api_response('error', 'Validation failed.', serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)

    event.delete()
    return api_response('success', 'Event deleted successfully.')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_event_approve(request, pk):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty and admin can approve events.', http_status=status.HTTP_403_FORBIDDEN)

    event = safe_get_object_or_404(Event, pk=pk)
    approval = request.data.get('approval_status')

    if approval not in ['approved', 'rejected']:
        return api_response('error', 'Approval status must be approved or rejected.', http_status=status.HTTP_400_BAD_REQUEST)

    event.approval_status = approval
    if approval == 'approved':
        event.status = 'published'
    event.save()

    # Notify organizer
    Notification.objects.create(
        user=event.organizer,
        title=f"Event {approval.capitalize()}",
        message=f"Your event '{event.title}' has been {approval} by {request.user.username}."
    )

    return api_response('success', f'Event has been {approval}.', EventSerializer(event).data)


# --- REGISTRATIONS & TICKET VERIFICATION API ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_registrations(request):
    if request.method == 'GET':
        if request.user.role == 'student':
            regs = Registration.objects.filter(student=request.user)
        else:
            regs = Registration.objects.all()
        serializer = RegistrationSerializer(regs, many=True)
        return api_response('success', 'Registrations retrieved.', serializer.data)

    event_id = request.data.get('event')
    event = safe_get_object_or_404(Event, pk=event_id)

    if event.approval_status != 'approved' or event.status != 'published':
        return api_response('error', 'Cannot register for unpublished or unapproved events.', http_status=status.HTTP_400_BAD_REQUEST)

    if timezone.now() > event.deadline:
        return api_response('error', 'Registration deadline for this event has passed.', http_status=status.HTTP_400_BAD_REQUEST)

    current_regs = Registration.objects.filter(event=event, status='Confirmed').count()
    if current_regs >= event.max_participants:
        return api_response('error', 'Event is already at maximum capacity.', http_status=status.HTTP_400_BAD_REQUEST)

    existing = Registration.objects.filter(student=request.user, event=event).first()
    if existing:
        if existing.status == 'Confirmed':
            return api_response('error', 'You are already registered for this event.', http_status=status.HTTP_400_BAD_REQUEST)
        else:
            existing.status = 'Confirmed'
            existing.save()
            reg = existing
    else:
        reg = Registration.objects.create(student=request.user, event=event, status='Confirmed')

    # Confirmation Notification
    Notification.objects.create(
        user=request.user,
        title="Registration Confirmed",
        message=f"You successfully registered for '{event.title}'. Digital Pass Ticket Code: {reg.ticket_code}"
    )

    serializer = RegistrationSerializer(reg)
    return api_response('success', 'Successfully registered for event.', serializer.data, http_status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_registration_cancel(request, pk):
    reg = safe_get_object_or_404(Registration, pk=pk)
    if reg.student != request.user and request.user.role not in ['admin', 'organizer']:
        return api_response('error', 'Unauthorized cancellation.', http_status=status.HTTP_403_FORBIDDEN)

    reg.status = 'Cancelled'
    reg.save()

    Notification.objects.create(
        user=reg.student,
        title="Registration Cancelled",
        message=f"Your registration for '{reg.event.title}' has been cancelled."
    )

    return api_response('success', 'Registration cancelled successfully.')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_verify_ticket(request):
    ticket_code = request.data.get('ticket_code')
    reg = Registration.objects.filter(ticket_code=ticket_code).first()

    if not reg:
        return api_response('error', 'Invalid ticket code.', http_status=status.HTTP_404_NOT_FOUND)

    serializer = RegistrationSerializer(reg)
    return api_response('success', 'Valid Digital Ticket Pass.', serializer.data)


# --- ATTENDANCE & CHECK-IN API ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_attendance(request):
    if request.method == 'GET':
        logs = Attendance.objects.all()
        serializer = AttendanceSerializer(logs, many=True)
        return api_response('success', 'Attendance records retrieved.', serializer.data)

    reg_id = request.data.get('registration')
    reg = safe_get_object_or_404(Registration, pk=reg_id)

    reg.attendance = 'present'
    reg.save()

    att, _ = Attendance.objects.get_or_create(registration=reg, defaults={'verified_by': request.user})
    serializer = AttendanceSerializer(att)
    return api_response('success', f'Attendance marked present for {reg.student.username}.', serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_attendance_checkin(request):
    if request.user.role not in ['organizer', 'faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Unauthorized to perform check-in scanning.', http_status=status.HTTP_403_FORBIDDEN)

    ticket_code = request.data.get('ticket_code')
    reg = Registration.objects.filter(ticket_code=ticket_code).first()

    if not reg:
        return api_response('error', 'Invalid Ticket Code. Entry Denied.', http_status=status.HTTP_404_NOT_FOUND)

    if reg.status != 'Confirmed':
        return api_response('error', 'Registration status is not Confirmed.', http_status=status.HTTP_400_BAD_REQUEST)

    reg.attendance = 'present'
    reg.save()

    att, created = Attendance.objects.get_or_create(registration=reg, defaults={'verified_by': request.user})

    # Auto issue certificate
    cert_file = generate_certificate_pdf(reg.student, reg.event)
    Certificate.objects.get_or_create(
        student=reg.student,
        event=reg.event,
        defaults={'certificate_file': cert_file}
    )

    Notification.objects.create(
        user=reg.student,
        title="Event Check-in Confirmed & Certificate Issued",
        message=f"Attendance confirmed for '{reg.event.title}'. Your participation certificate is ready for download!"
    )

    return api_response('success', f"Check-in verified for {reg.student.full_name} ({reg.student.roll_number}).", {
        'student': reg.student.full_name,
        'event': reg.event.title,
        'ticket_code': reg.ticket_code,
        'checked_in_at': att.checked_in_at
    })


# --- FEEDBACK & CERTIFICATES API ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_feedback(request):
    if request.method == 'GET':
        feedbacks = Feedback.objects.all()
        serializer = FeedbackSerializer(feedbacks, many=True)
        return api_response('success', 'Feedback list retrieved.', serializer.data)

    event_id = request.data.get('event')
    rating = request.data.get('rating')
    comments = request.data.get('comments', '')

    event = safe_get_object_or_404(Event, pk=event_id)

    fb, created = Feedback.objects.update_or_create(
        student=request.user,
        event=event,
        defaults={'rating': rating, 'comments': comments}
    )

    return api_response('success', 'Feedback submitted successfully.', FeedbackSerializer(fb).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_certificates(request):
    certs = Certificate.objects.filter(student=request.user)
    serializer = CertificateSerializer(certs, many=True)
    return api_response('success', 'Certificates retrieved.', serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_download_certificate(request, pk):
    cert = safe_get_object_or_404(Certificate, pk=pk)
    if cert.student != request.user and request.user.role not in ['admin', 'organizer']:
        return api_response('error', 'Unauthorized certificate access.', http_status=status.HTTP_403_FORBIDDEN)

    reg = Registration.objects.filter(student=cert.student, event=cert.event, status='Confirmed').first()
    if reg and reg.attendance_status != 'approved':
        return api_response('error', 'Certificate download is locked until department faculty approves your attendance.', http_status=status.HTTP_400_BAD_REQUEST)

    rel_path = generate_certificate_pdf(cert.student, cert.event)
    cert.certificate_file = rel_path
    cert.save()
    file_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{cert.student.username}_{cert.event.event_id}.txt"'
    return response


# --- NOTIFICATIONS API ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_notifications(request):
    if request.method == 'GET':
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifs, many=True)
        return api_response('success', 'Notifications list.', serializer.data)

    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return api_response('success', 'All notifications marked as read.')


# --- ADMIN & REPORTS API ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard_reports(request):
    if request.user.role not in ['admin', 'faculty', 'organizer'] and not request.user.is_superuser:
        return api_response('error', 'Unauthorized report access.', http_status=status.HTTP_403_FORBIDDEN)

    analytics = get_dashboard_analytics()
    return api_response('success', 'Analytics overview.', analytics)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_export_report_csv(request):
    if request.user.role not in ['admin', 'faculty', 'organizer'] and not request.user.is_superuser:
        return api_response('error', 'Unauthorized CSV export.', http_status=status.HTTP_403_FORBIDDEN)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Campus_Event_Report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Event ID', 'Title', 'Category', 'Date', 'Venue', 'Status', 'Approval Status', 'Registrations'])

    events = Event.objects.all()
    for e in events:
        writer.writerow([
            e.event_id,
            e.title,
            e.category.name,
            e.date,
            e.venue.venue_name if e.venue else 'N/A',
            e.status,
            e.approval_status,
            e.registrations.filter(status='Confirmed').count()
        ])

    return response


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_admin_manage_users(request, pk=None):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return api_response('error', 'Admin permission required.', http_status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        users = User.objects.all()
        serializer = CustomUserSerializer(users, many=True)
        return api_response('success', 'Users list.', serializer.data)

    if request.method == 'DELETE' and pk:
        u = get_object_or_404(User, pk=pk)
        u.delete()
        return api_response('success', 'User deleted successfully.')

    return api_response('error', 'Invalid action.', http_status=status.HTTP_400_BAD_REQUEST)


# --- PAID REGISTRATION FLOW (INITIATE & CONFIRM) ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_initiate_registration(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if event.approval_status != 'approved' or event.status != 'published':
        return api_response('error', 'Cannot register for unpublished or unapproved events.', http_status=status.HTTP_400_BAD_REQUEST)

    if timezone.now() > event.deadline:
        return api_response('error', 'Registration deadline for this event has passed.', http_status=status.HTTP_400_BAD_REQUEST)

    try:
        num_members = int(request.data.get('num_members', 1))
        if num_members < 1:
            return api_response('error', 'Number of members must be at least 1.', http_status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError):
        return api_response('error', 'Invalid member count provided.', http_status=status.HTTP_400_BAD_REQUEST)

    existing = Registration.objects.filter(student=request.user, event=event, status='Confirmed').first()
    if existing:
        return api_response('error', 'You are already registered for this event.', http_status=status.HTTP_400_BAD_REQUEST)

    from django.db.models import Sum
    total_registered_seats = event.registrations.filter(status='Confirmed').aggregate(total=Sum('num_members'))['total'] or 0
    remaining_seats = event.max_participants - total_registered_seats

    if remaining_seats <= 0:
        return api_response('error', 'Event is already at maximum capacity.', http_status=status.HTTP_400_BAD_REQUEST)

    if num_members > remaining_seats:
        return api_response('error', f'Only {remaining_seats} seat(s) remaining for this event.', http_status=status.HTTP_400_BAD_REQUEST)

    unit_fee = float(event.registration_fee)
    total_amount = round(unit_fee * num_members, 2)

    if event.payment_scanner:
        qr_code_url = request.build_absolute_uri(event.payment_scanner.url)
    else:
        import urllib.parse
        qr_text = f"Pay ₹{total_amount:.2f} for {event.title} ({num_members} member{'s' if num_members > 1 else ''})"
        qr_code_url = f"https://quickchart.io/qr?text={urllib.parse.quote(qr_text)}&size=250"

    return api_response('success', 'Registration initiated.', {
        'event_id': event.event_id,
        'event_title': event.title,
        'num_members': num_members,
        'unit_fee': unit_fee,
        'total_amount': total_amount,
        'qr_code_url': qr_code_url,
        'has_custom_scanner': bool(event.payment_scanner),
        'remaining_seats': remaining_seats
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_confirm_registration(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if event.approval_status != 'approved' or event.status != 'published':
        return api_response('error', 'Cannot register for unpublished or unapproved events.', http_status=status.HTTP_400_BAD_REQUEST)

    if timezone.now() > event.deadline:
        return api_response('error', 'Registration deadline for this event has passed.', http_status=status.HTTP_400_BAD_REQUEST)

    try:
        num_members = int(request.data.get('num_members', 1))
        if num_members < 1:
            return api_response('error', 'Number of members must be at least 1.', http_status=status.HTTP_400_BAD_REQUEST)
    except (TypeError, ValueError):
        return api_response('error', 'Invalid member count provided.', http_status=status.HTTP_400_BAD_REQUEST)

    from django.db.models import Sum
    total_registered_seats = event.registrations.filter(status='Confirmed').aggregate(total=Sum('num_members'))['total'] or 0
    remaining_seats = event.max_participants - total_registered_seats

    if num_members > remaining_seats:
        return api_response('error', f'Registration failed: Only {remaining_seats} seat(s) remaining.', http_status=status.HTTP_400_BAD_REQUEST)

    # Verification: Require payment screenshot proof for paid events / events with payment scanner
    payment_screenshot = request.FILES.get('payment_screenshot')
    if (event.registration_fee > 0 or event.payment_scanner) and not payment_screenshot:
        return api_response('error', 'Payment screenshot proof is required to complete registration.', http_status=status.HTTP_400_BAD_REQUEST)

    import uuid
    payment_id = request.data.get('payment_id') or f"PAY-TXN-{uuid.uuid4().hex[:10].upper()}"
    unit_fee = float(event.registration_fee)
    total_amount = round(unit_fee * num_members, 2)

    existing = Registration.objects.filter(student=request.user, event=event).first()
    if existing:
        if existing.status == 'Confirmed':
            return api_response('error', 'You are already registered for this event.', http_status=status.HTTP_400_BAD_REQUEST)
        existing.status = 'Confirmed'
        existing.num_members = num_members
        existing.amount_paid = total_amount
        existing.payment_status = 'paid'
        existing.payment_id = payment_id
        if payment_screenshot:
            existing.payment_screenshot = payment_screenshot
        existing.attendance_status = 'pending'
        existing.save()
        reg = existing
    else:
        reg = Registration.objects.create(
            student=request.user,
            event=event,
            num_members=num_members,
            amount_paid=total_amount,
            payment_status='paid',
            payment_id=payment_id,
            payment_screenshot=payment_screenshot,
            status='Confirmed',
            attendance_status='pending'
        )

    Notification.objects.create(
        user=request.user,
        title="Registration & Payment Confirmed",
        message=f"Registered for '{event.title}' with {num_members} member(s). Paid ₹{total_amount:.2f} (Ref: {payment_id}). Ticket Code: {reg.ticket_code}"
    )

    serializer = RegistrationSerializer(reg)
    return api_response('success', 'Registration and payment confirmed successfully.', serializer.data, http_status=status.HTTP_201_CREATED)


# --- DEPARTMENT-BASED FACULTY ATTENDANCE APPROVALS ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_pending_department_attendance(request):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can access pending attendance approvals.', http_status=status.HTTP_403_FORBIDDEN)

    regs = Registration.objects.filter(status='Confirmed', attendance_status='pending')

    if request.user.role == 'faculty' and request.user.department:
        regs = regs.filter(student__department=request.user.department)

    serializer = RegistrationSerializer(regs, many=True)
    return api_response('success', 'Pending attendance requests retrieved.', serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_approve_attendance(request, pk):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can approve student attendance.', http_status=status.HTTP_403_FORBIDDEN)

    reg = get_object_or_404(Registration, pk=pk)

    if request.user.role == 'faculty' and request.user.department:
        if reg.student.department != request.user.department:
            return api_response('error', 'You can only approve attendance for students in your own department.', http_status=status.HTTP_403_FORBIDDEN)

    reg.attendance_status = 'approved'
    reg.attendance = 'present'
    reg.approved_by = request.user
    reg.save()

    Attendance.objects.get_or_create(registration=reg, defaults={'verified_by': request.user})

    cert_file = generate_certificate_pdf(reg.student, reg.event)
    Certificate.objects.get_or_create(
        student=reg.student,
        event=reg.event,
        defaults={'certificate_file': cert_file}
    )

    Notification.objects.create(
        user=reg.student,
        title="Department Attendance Approved!",
        message=f"Faculty {request.user.full_name} from {request.user.department.name if request.user.department else 'your department'} has approved your attendance for '{reg.event.title}'. Your certificate is now ready for download!"
    )

    return api_response('success', f"Attendance approved for {reg.student.full_name}.", RegistrationSerializer(reg).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_reject_attendance(request, pk):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can reject student attendance.', http_status=status.HTTP_403_FORBIDDEN)

    reg = get_object_or_404(Registration, pk=pk)

    if request.user.role == 'faculty' and request.user.department:
        if reg.student.department != request.user.department:
            return api_response('error', 'You can only reject attendance for students in your own department.', http_status=status.HTTP_403_FORBIDDEN)

    reg.attendance_status = 'rejected'
    reg.attendance = 'absent'
    reg.approved_by = request.user
    reg.save()

    Notification.objects.create(
        user=reg.student,
        title="Attendance Request Rejected",
        message=f"Your attendance request for '{reg.event.title}' was rejected by faculty."
    )

    return api_response('success', f"Attendance rejected for {reg.student.full_name}.", RegistrationSerializer(reg).data)


# --- DEDICATED FACULTY ATTENDANCE APPROVAL API ENDPOINTS ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_faculty_attendance_approvals(request):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can access attendance approvals.', http_status=status.HTTP_403_FORBIDDEN)

    regs = Registration.objects.filter(status='Confirmed')

    # Filter to only show students belonging to the faculty's department
    if request.user.role == 'faculty' and request.user.department:
        regs = regs.filter(student__department=request.user.department)

    # Optional filter params: ?status=pending|approved|rejected and ?event=<id>
    status_filter = request.query_params.get('status')
    event_filter = request.query_params.get('event')

    # Calculate summary counts for all department students
    total_pending = regs.filter(attendance_status='pending').count()
    total_approved = regs.filter(attendance_status='approved').count()
    total_rejected = regs.filter(attendance_status='rejected').count()

    regs_filtered = regs
    if status_filter and status_filter in ['pending', 'approved', 'rejected']:
        regs_filtered = regs_filtered.filter(attendance_status=status_filter)

    if event_filter and event_filter.isdigit():
        regs_filtered = regs_filtered.filter(event_id=event_filter)

    serializer = RegistrationSerializer(regs_filtered, many=True, context={'request': request})

    return api_response('success', 'Faculty attendance approvals retrieved.', {
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'registrations': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_faculty_approve_attendance(request, pk):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can approve student attendance.', http_status=status.HTTP_403_FORBIDDEN)

    reg = get_object_or_404(Registration, pk=pk)

    if request.user.role == 'faculty' and request.user.department:
        if reg.student.department != request.user.department:
            return api_response('error', 'Permission Denied. You can only approve attendance for students in your own department.', http_status=status.HTTP_403_FORBIDDEN)

    reg.attendance_status = 'approved'
    reg.attendance = 'present'
    reg.approved_by = request.user
    reg.save()

    Attendance.objects.get_or_create(registration=reg, defaults={'verified_by': request.user})

    cert_file = generate_certificate_pdf(reg.student, reg.event)
    Certificate.objects.get_or_create(
        student=reg.student,
        event=reg.event,
        defaults={'certificate_file': cert_file}
    )

    Notification.objects.create(
        user=reg.student,
        title="Department Attendance Approved!",
        message=f"Faculty {request.user.full_name} has approved your attendance for '{reg.event.title}'. Your certificate is now ready for download!"
    )

    return api_response('success', f"Attendance approved for {reg.student.full_name}.", RegistrationSerializer(reg, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_faculty_reject_attendance(request, pk):
    if request.user.role not in ['faculty', 'admin'] and not request.user.is_superuser:
        return api_response('error', 'Only faculty members can reject student attendance.', http_status=status.HTTP_403_FORBIDDEN)

    reg = get_object_or_404(Registration, pk=pk)

    if request.user.role == 'faculty' and request.user.department:
        if reg.student.department != request.user.department:
            return api_response('error', 'Permission Denied. You can only reject attendance for students in your own department.', http_status=status.HTTP_403_FORBIDDEN)

    reg.attendance_status = 'rejected'
    reg.attendance = 'absent'
    reg.approved_by = request.user
    reg.save()

    Notification.objects.create(
        user=reg.student,
        title="Attendance Request Rejected",
        message=f"Your attendance request for '{reg.event.title}' was rejected by faculty."
    )

    return api_response('success', f"Attendance rejected for {reg.student.full_name}.", RegistrationSerializer(reg, context={'request': request}).data)


