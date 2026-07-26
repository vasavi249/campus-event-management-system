from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from events.models import Department, Category, Club, Venue, Event, Registration, Notification

User = get_user_model()

class CampusEventSystemTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name="Computer Science", code="CSE")
        self.category = Category.objects.create(name="Technical", description="Tech events")
        self.club = Club.objects.create(name="Coding Club", description="Coding activities", department=self.dept)
        self.venue = Venue.objects.create(venue_name="Main Seminar Hall", building="Tech Block A", capacity=100)
        
        self.organizer = User.objects.create_user(
            username="organizer", email="org@campus.edu", password="orgpassword", 
            role="organizer", department=self.dept, club=self.club
        )
        self.faculty = User.objects.create_user(
            username="faculty", email="fac@campus.edu", password="facpassword", 
            role="faculty", department=self.dept
        )
        self.student = User.objects.create_user(
            username="student", email="stud@campus.edu", password="studpassword", 
            role="student", roll_number="CSE-001", department=self.dept
        )

    def test_user_creation_and_roles(self):
        self.assertEqual(self.student.role, "student")
        self.assertEqual(self.organizer.role, "organizer")
        self.assertEqual(self.faculty.role, "faculty")
        self.assertEqual(self.student.roll_number, "CSE-001")

    def test_event_deadline_validation(self):
        event_date = timezone.now().date() + timedelta(days=2)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=1)
        
        event = Event(
            title="Seminar", category=self.category, description="desc", 
            venue=self.venue, date=event_date, time=event_time, 
            deadline=deadline, max_participants=10, organizer=self.organizer,
            department=self.dept, club=self.club
        )
        try:
            event.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly!")

        invalid_deadline = timezone.now() + timedelta(days=3)
        invalid_event = Event(
            title="Seminar Invalid", category=self.category, description="desc", 
            venue=self.venue, date=event_date, time=event_time, 
            deadline=invalid_deadline, max_participants=10, organizer=self.organizer,
            department=self.dept, club=self.club
        )
        with self.assertRaises(ValidationError):
            invalid_event.clean()

    def test_event_skills_learned_property(self):
        event_date = timezone.now().date() + timedelta(days=5)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=3)
        
        event = Event.objects.create(
            title="Python AI Bootcamp", category=self.category, description="AI Skills Event", 
            venue=self.venue, date=event_date, time=event_time, 
            deadline=deadline, max_participants=50, organizer=self.organizer,
            department=self.dept, club=self.club, status="published", approval_status="approved",
            skills_learned="Python, PyTorch, Artificial Intelligence"
        )
        self.assertEqual(len(event.skills_list), 3)
        self.assertIn("Python", event.skills_list)
        self.assertIn("PyTorch", event.skills_list)

    def test_student_registration_and_capacity(self):
        event_date = timezone.now().date() + timedelta(days=5)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=3)
        
        event = Event.objects.create(
            title="Coding Contest", category=self.category, description="Contest description", 
            venue=self.venue, date=event_date, time=event_time, 
            deadline=deadline, max_participants=1, organizer=self.organizer,
            department=self.dept, club=self.club, status="published", approval_status="approved"
        )
        
        reg = Registration(student=self.student, event=event)
        reg.clean()
        reg.save()
        self.assertEqual(event.registrations.count(), 1)
        self.assertTrue(reg.ticket_code.startswith("EVT-"))
        
        student2 = User.objects.create_user(
            username="student2", email="stud2@campus.edu", password="studpassword", 
            role="student", roll_number="CSE-002", department=self.dept
        )
        reg2 = Registration(student=student2, event=event)
        with self.assertRaises(ValidationError):
            reg2.clean()

    def test_attendance_marking_and_notifications(self):
        event_date = timezone.now().date() + timedelta(days=2)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=1)
        
        event = Event.objects.create(
            title="Tech Talk", category=self.category, description="Talk description", 
            venue=self.venue, date=event_date, time=event_time, 
            deadline=deadline, max_participants=10, organizer=self.organizer,
            department=self.dept, club=self.club, status="published", approval_status="approved"
        )
        
        self.client.force_login(self.student)
        
        response = self.client.post('/api/registrations/', {'event': event.event_id}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        reg = Registration.objects.get(student=self.student, event=event)
        reg.attendance = "present"
        reg.save()
        
        self.assertEqual(reg.attendance, "present")
        
        notifications = Notification.objects.filter(user=self.student, title="Registration Confirmed")
        self.assertTrue(notifications.exists())

    def test_paid_registration_flow_and_department_attendance(self):
        event_date = timezone.now().date() + timedelta(days=4)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=2)

        paid_event = Event.objects.create(
            title="Paid AI Workshop", category=self.category, description="Hands-on workshop",
            venue=self.venue, date=event_date, time=event_time,
            deadline=deadline, max_participants=10, registration_fee=150.00,
            organizer=self.organizer, department=self.dept, club=self.club,
            status="published", approval_status="approved"
        )

        # 1. Initiate Paid Registration for 2 members
        self.client.force_login(self.student)
        init_res = self.client.post(
            f'/api/events/{paid_event.event_id}/registration/initiate/',
            {'num_members': 2}, content_type='application/json'
        )
        self.assertEqual(init_res.status_code, 200)
        self.assertEqual(init_res.json()['data']['total_amount'], 300.00)

        # 2. Confirm Paid Registration with Screenshot Proof
        import base64
        from django.core.files.uploadedfile import SimpleUploadedFile
        gif_bytes = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        uploaded_screenshot = SimpleUploadedFile("test_proof.gif", gif_bytes, content_type="image/gif")

        confirm_res = self.client.post(
            f'/api/events/{paid_event.event_id}/registration/confirm/',
            {'num_members': 2, 'payment_id': 'PAY-TEST-999', 'payment_screenshot': uploaded_screenshot}
        )
        self.assertEqual(confirm_res.status_code, 201)
        reg = Registration.objects.get(student=self.student, event=paid_event)
        self.assertEqual(reg.num_members, 2)
        self.assertEqual(float(reg.amount_paid), 300.00)
        self.assertIsNotNone(reg.payment_screenshot)
        self.assertEqual(reg.attendance_status, 'pending')

        # 3. Department Faculty Views Pending Attendance
        self.client.force_login(self.faculty)
        pending_res = self.client.get('/api/attendance/pending/')
        self.assertEqual(pending_res.status_code, 200)
        self.assertEqual(len(pending_res.json()['data']), 1)

        # 4. Department Faculty Approves Attendance
        approve_res = self.client.post(f'/api/attendance/{reg.registration_id}/approve/')
        self.assertEqual(approve_res.status_code, 200)

        reg.refresh_from_db()
        self.assertEqual(reg.attendance_status, 'approved')
        self.assertEqual(reg.approved_by, self.faculty)

        # 5. Other Department Faculty Attempting Approval Should Be Rejected
        mech_dept = Department.objects.create(name="Mechanical", code="ME")
        other_faculty = User.objects.create_user(
            username="faculty_me", email="me@campus.edu", password="password",
            role="faculty", department=mech_dept
        )
        reg.attendance_status = 'pending'
        reg.save()

        self.client.force_login(other_faculty)
        forbidden_res = self.client.post(f'/api/attendance/{reg.registration_id}/approve/')
        self.assertEqual(forbidden_res.status_code, 403)

    def test_category_filter_and_faculty_attendance_approvals_api(self):
        # 1. Test Server-side Category Query Filter on GET /api/events/
        res_cat = self.client.get('/api/events/?category=Technical')
        self.assertEqual(res_cat.status_code, 200)

        # 2. Test Faculty Attendance Approvals API with Summary Counts
        event_date = timezone.now().date() + timedelta(days=3)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=1)

        evt = Event.objects.create(
            title="Dept Workshop", category=self.category, description="Desc",
            venue=self.venue, date=event_date, time=event_time, deadline=deadline,
            max_participants=20, organizer=self.organizer, department=self.dept, club=self.club,
            status="published", approval_status="approved"
        )
        reg = Registration.objects.create(student=self.student, event=evt, status='Confirmed', attendance_status='pending')

        self.client.force_login(self.faculty)
        res_approvals = self.client.get('/api/faculty/attendance-approvals/')
        self.assertEqual(res_approvals.status_code, 200)
        self.assertEqual(res_approvals.json()['data']['total_pending'], 1)

        # 3. Approve via Dedicated Endpoint
        res_app = self.client.post(f'/api/faculty/attendance-approvals/{reg.registration_id}/approve/')
        self.assertEqual(res_app.status_code, 200)

        reg.refresh_from_db()
        self.assertEqual(reg.attendance_status, 'approved')
        self.assertEqual(reg.approved_by, self.faculty)

        # 4. Reject via Dedicated Endpoint
        res_rej = self.client.post(f'/api/faculty/attendance-approvals/{reg.registration_id}/reject/')
        self.assertEqual(res_rej.status_code, 200)

        reg.refresh_from_db()
        self.assertEqual(reg.attendance_status, 'rejected')

    def test_event_banner_image_upload(self):
        import base64
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.organizer)

        gif_bytes = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        uploaded_image = SimpleUploadedFile("test_banner.gif", gif_bytes, content_type="image/gif")

        event_date = timezone.now().date() + timedelta(days=6)
        event_time = timezone.now().time()
        deadline = timezone.now() + timedelta(days=4)

        response = self.client.post('/api/events/', {
            'title': 'Event With Poster',
            'category': self.category.id,
            'venue': self.venue.venue_id,
            'date': str(event_date),
            'time': str(event_time),
            'deadline': deadline.strftime('%Y-%m-%dT%H:%M'),
            'max_participants': 50,
            'description': 'Banner Upload Test',
            'status': 'published',
            'approval_status': 'approved',
            'banner_image': uploaded_image
        })

        self.assertEqual(response.status_code, 201)
        data = response.json()['data']
        self.assertIsNotNone(data['banner_image_url'])



