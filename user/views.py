from datetime import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, UpdateView

from leave.models import EmployeeLeave, LeaveType
from utils.common import point_down_round
from utils.date_converter import nepali_str_to_english
from .models import AuthUser, Profile, WorkingDetail, GENDER, MARITAL_STATUS, JobType, Document, Payout
from .forms import ProfileForm, UserForm, WorkingDetailForm, DocumentForm, PayoutForm
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import transaction
from branch.models import District

class EmployeeListView(ListView):
    model = AuthUser  
    template_name = 'user/employee/list.html'
    context_object_name = 'employees'
    paginate_by = 10


    def get_queryset(self):
        queryset = AuthUser.objects.filter(is_active=True).select_related('profile', 'working_detail').order_by('-id')
        
        # Get filter parameters from either POST or GET
        request_data = self.request.POST if self.request.method == 'POST' else self.request.GET
        
        username = request_data.get('username')
        gender = request_data.get('gender')
        marital_status = request_data.get('marital_status')
        job_type = request_data.get('job_type')

        # Apply filters
        if username:
            queryset = queryset.filter(profile__user__username__icontains=username)
        if gender:
            queryset = queryset.filter(profile__gender=gender)
        if marital_status:
            queryset = queryset.filter(profile__marital_status=marital_status)
        if job_type:
            queryset = queryset.filter(working_detail__job_type=job_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genders'] = GENDER
        context['marital_statuses'] = MARITAL_STATUS
        context['job_types'] = JobType.choices
        
        # Get list of usernames for the select dropdown
        context['usernames'] = AuthUser.objects.filter(is_active=True).values_list('username', flat=True).distinct().order_by('username')
        
        # Add current filter values to context from either POST or GET
        request_data = self.request.POST if self.request.method == 'POST' else self.request.GET
        context['current_username'] = request_data.get('username', '')
        context['current_gender'] = request_data.get('gender', '')
        context['current_marital_status'] = request_data.get('marital_status', '')
        context['current_job_type'] = request_data.get('job_type', '')
        
        return context

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class EmployeeCreateView(View):
    template_name = 'user/employee/create.html'
    success_url = reverse_lazy('user:employee_list')

    def get(self, request):
        context = {
            'user_form': UserForm(prefix='user'),
            'profile_form': ProfileForm(prefix='profile'),
            'working_form': WorkingDetailForm(prefix='work'),
            'document_form': DocumentForm(),
            'payout_form': PayoutForm(),
            'documents': [],
            'payouts': [],
            'action': 'Create'  
        }
        return render(request, self.template_name, context)

    def post(self, request):
        section = request.POST.get('form_section')

        if section == 'profile':
            user_form = UserForm(request.POST, prefix='user')
            profile_form = ProfileForm(request.POST, prefix='profile')

            if user_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        user = user_form.save(commit=False)
                        user.set_password('deli@gbl2079')  # Set default password
                        user.save()

                        profile = profile_form.save(commit=False)
                        profile.user = user
                        profile_picture = request.FILES.get('profile-profile_picture')
                        if profile_picture:
                            profile.profile_picture = profile_picture
                        profile.save()

                        request.session['new_user_id'] = user.id
                        messages.success(request, "Profile details saved successfully.")
                        return redirect('user:employee_list')
                except Exception as e:
                    messages.error(request, f"Error creating employee: {str(e)}")
            else:
                # Display specific form errors
                if not user_form.is_valid():
                    for field, errors in user_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                if not profile_form.is_valid():
                    for field, errors in profile_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

        elif section == 'document':
            user_id = request.session.get('new_user_id')
            if not user_id:
                messages.error(request, "Please complete profile information first.")
                return redirect('user:employee_create')
            
            user = get_object_or_404(AuthUser, id=user_id)
            
            # Get all document forms from the request
            document_forms = []
            for key in request.FILES:
                if key.startswith('document_file-'):
                    index = key.split('-')[1]
                    document_type = request.POST.get(f'document_type-{index}')
                    document_file = request.FILES.get(f'document_file-{index}')
                    issue_date = request.POST.get(f'issue_date-{index}')
                    issue_body = request.POST.get(f'issue_body-{index}')
                    
                    if document_type and document_file:
                        document_forms.append({
                            'document_type': document_type,
                            'document_file': document_file,
                            'issue_date': issue_date,
                            'issue_body': issue_body
                        })
            
            if not document_forms:
                messages.error(request, "Please select at least one document to upload.")
                return redirect(f"{reverse('user:employee_create')}?tab=document")
            
            success_count = 0
            for form_data in document_forms:
                try:
                    # Convert Nepali date to English date
                    issue_date = None
                    if form_data['issue_date'] and form_data['document_type'] != 'resume':
                        try:
                            issue_date = nepali_str_to_english(form_data['issue_date'])
                        except Exception as e:
                            messages.error(request, f"Invalid date format for document {form_data['document_type']}: {str(e)}")
                            continue

                    # Convert issue_body ID to District instance
                    issue_body = None
                    if form_data['issue_body'] and form_data['document_type'] != 'resume':
                        try:
                            issue_body = District.objects.get(id=form_data['issue_body'])
                        except District.DoesNotExist:
                            messages.error(request, f"Invalid district ID for document {form_data['document_type']}")
                            continue

                    document = Document(
                        user=user,
                        document_type=form_data['document_type'],
                        document_file=form_data['document_file'],
                        issue_date=issue_date,
                        issue_body=issue_body
                    )
                    document.save()
                    success_count += 1
                except Exception as e:
                    messages.error(request, f"Error uploading document: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f"{success_count} document uploaded successfully.")
            
            return redirect(f"{reverse('user:employee_create')}?tab=document")

        elif section == 'payout':
            user_id = request.session.get('new_user_id')
            if not user_id:
                messages.error(request, "Please complete profile information first.")
                return redirect('user:employee_create')
            
            user = get_object_or_404(AuthUser, id=user_id)
            
            # Check if payout exists for this user and payout_interval
            payout_interval_id = request.POST.get('payout_interval')
            existing_payout = None
            if payout_interval_id:
                existing_payout = Payout.objects.filter(user=user, payout_interval_id=payout_interval_id).first()
            
            payout_form = PayoutForm(request.POST, instance=existing_payout)
            
            if payout_form.is_valid():
                try:
                    payout = payout_form.save(commit=False)
                    payout.user = user
                    payout.created_by = request.user
                    payout.save()
                    messages.success(request, "Payout details saved successfully.")
                except Exception as e:
                    messages.error(request, f"Error saving payout: {str(e)}")
            else:
                messages.error(request, "Please correct the payout form errors.")
            
            return redirect(f"{reverse('user:employee_create')}?tab=payout")

        return redirect('user:employee_create')


class EmployeeEditView(UpdateView):
    template_name = 'user/employee/create.html'
    success_url = reverse_lazy('user:employee_list')

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(AuthUser, pk=kwargs['pk'])
        profile, _ = Profile.objects.get_or_create(user=user)
        working_detail, _ = WorkingDetail.objects.get_or_create(employee=user)

        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)
        working_form = WorkingDetailForm(instance=working_detail)
        document_form = DocumentForm()
        
        # Check if payout exists and prefill the form
        payout = Payout.objects.filter(user=user).first()
        payout_form = PayoutForm(instance=payout) if payout else PayoutForm()
        
        documents = Document.objects.filter(user=user)
        payouts = Payout.objects.filter(user=user)
        
        # Get list of already uploaded document types
        uploaded_document_types = documents.values_list('document_type', flat=True)

        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'working_form': working_form,
            'document_form': document_form,
            'payout_form': payout_form,
            'documents': documents,
            'payouts': payouts,
            'profile': profile,
            'action': 'Update',
            'uploaded_document_types': uploaded_document_types,
            'profile_picture': profile.profile_picture if profile.profile_picture else None
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(AuthUser, pk=kwargs['pk'])
        profile, _ = Profile.objects.get_or_create(user=user)
        working_detail, _ = WorkingDetail.objects.get_or_create(employee=user)

        section = request.POST.get('form_section')
        
        if section == 'profile':
            user_form = UserForm(request.POST, instance=user)
            profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
            working_form = WorkingDetailForm(instance=working_detail)

            if user_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        user = user_form.save()

                        profile = profile_form.save(commit=False)
                        profile.user = user
                        # Handle profile picture upload
                        if 'profile-profile_picture' in request.FILES:
                            profile.profile_picture = request.FILES['profile-profile_picture']

                        profile.save()

                        if profile:
                            assignLeaveToEmployee(user)
                        
                        messages.success(request, "Profile details updated successfully.")
                        return redirect('user:employee_list')
                except Exception as e:
                    messages.error(request, f"Error updating profile: {str(e)}")
            else:
                # Display specific form errors
                if not user_form.is_valid():
                    for field, errors in user_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
                if not profile_form.is_valid():
                    for field, errors in profile_form.errors.items():
                        for error in errors:
                            messages.error(request, f"{field.replace('_', ' ').title()}: {error}")

        elif section == 'work':
            user_form = UserForm(instance=user)
            profile_form = ProfileForm(instance=profile)
            working_form = WorkingDetailForm(request.POST, instance=working_detail)

            if working_form.is_valid():
                try:
                    with transaction.atomic():
                        working_detail = working_form.save(commit=False)
                        working_detail.employee = user
                        working_detail.save()
                        if working_detail:
                            assignLeaveToEmployee(user)

                        messages.success(request, "Work details updated successfully.")
                        return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=work")
                except Exception as e:
                    messages.error(request, f"Error updating work details: {str(e)}")
            else:
                messages.error(request, "Please correct the errors below.")

        elif section == 'document':
            user_form = UserForm(instance=user)
            profile_form = ProfileForm(instance=profile)
            working_form = WorkingDetailForm(instance=working_detail)
            
            # Get all document forms from the request
            document_forms = []
            for key in request.FILES:
                if key.startswith('document_file-'):
                    index = key.split('-')[1]
                    document_type = request.POST.get(f'document_type-{index}')
                    document_file = request.FILES.get(f'document_file-{index}')
                    issue_date = request.POST.get(f'issue_date-{index}')
                    issue_body = request.POST.get(f'issue_body-{index}')
                    
                    if document_type and document_file:
                        document_forms.append({
                            'document_type': document_type,
                            'document_file': document_file,
                            'issue_date': issue_date,
                            'issue_body': issue_body
                        })
            
            if not document_forms:
                messages.error(request, "Please select at least one document to upload.")
                return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")
            
            success_count = 0
            for form_data in document_forms:
                try:
                    # Convert Nepali date to English date
                    issue_date = None
                    if form_data['issue_date'] and form_data['document_type'] != 'resume':
                        try:
                            issue_date = nepali_str_to_english(form_data['issue_date'])
                        except Exception as e:
                            messages.error(request, f"Invalid date format for document {form_data['document_type']}: {str(e)}")
                            continue

                    # Convert issue_body ID to District instance
                    issue_body = None
                    if form_data['issue_body'] and form_data['document_type'] != 'resume':
                        try:
                            issue_body = District.objects.get(id=form_data['issue_body'])
                        except District.DoesNotExist:
                            messages.error(request, f"Invalid district ID for document {form_data['document_type']}")
                            continue

                    document = Document(
                        user=user,
                        document_type=form_data['document_type'],
                        document_file=form_data['document_file'],
                        issue_date=issue_date,
                        issue_body=issue_body
                    )
                    document.save()
                    success_count += 1
                except Exception as e:
                    messages.error(request, f"Error uploading document: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f"{success_count} document(s) uploaded successfully.")
            
            return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")

        elif section == 'payout':
            user_form = UserForm(instance=user)
            profile_form = ProfileForm(instance=profile)
            working_form = WorkingDetailForm(instance=working_detail)
            
            # Check if payout exists for this user and payout_interval
            payout_interval_id = request.POST.get('payout_interval')
            existing_payout = None
            if payout_interval_id:
                existing_payout = Payout.objects.filter(user=user, payout_interval_id=payout_interval_id).first()
            
            payout_form = PayoutForm(request.POST, instance=existing_payout)
            
            if payout_form.is_valid():
                try:
                    payout = payout_form.save(commit=False)
                    payout.user = user
                    payout.created_by = request.user
                    payout.save()
                    messages.success(request, "Payout details saved successfully.")
                except Exception as e:
                    messages.error(request, f"Error saving payout: {str(e)}")
            else:
                messages.error(request, "Please correct the payout form errors.")
            
            return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=payout")

        return redirect('user:employee_edit', pk=user.id)


class EmployeeDeleteView(View):
    model = AuthUser
    success_url = reverse_lazy('user:employee_list')

    def get_object(self):
        return get_object_or_404(self.model, pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        user = self.get_object()

        # Delete related Profile and WorkingDetail if exist
        profile = getattr(user, 'profile', None)
        if profile:
            profile.delete()

        try:
            working_detail = WorkingDetail.objects.get(employee=user)
            working_detail.delete()
        except WorkingDetail.DoesNotExist:
            pass

        # Delete all associated documents
        Document.objects.filter(user=user).delete()

        # Delete all associated payouts
        Payout.objects.filter(user=user).delete()

        user.delete()

        messages.success(request, "Team member and related data deleted successfully.")
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

class EmployeeDetailView(View):
    template_name = 'user/employee/detail.html'

    def get(self, request, pk):
        employee = get_object_or_404(AuthUser, pk=pk, is_active=True)
        profile = getattr(employee, 'profile', None)
        working_detail = getattr(employee, 'working_detail', None)
        documents = Document.objects.filter(user=employee)
        payouts = Payout.objects.filter(user=employee)
        
        context = {
            'employee': employee,
            'profile': profile,
            'working_detail': working_detail,
            'documents': documents,
            'payouts': payouts,
        }
        return render(request, self.template_name, context)

class DeleteDocumentView(View):
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        user = document.user
        document.delete()
        messages.success(request, "Document deleted successfully.")
        return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")

class EditDocumentView(View):
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        user = document.user
        
        # Get form data
        document_type = request.POST.get('document_type')
        document_file = request.FILES.get('document_file')
        issue_date = request.POST.get('issue_date')
        issue_body = request.POST.get('issue_body')
        
        try:
            # Update document fields
            if document_type:
                document.document_type = document_type
                # Clear issue date and issuing authority for Resume documents
                if document_type == 'resume':
                    document.issue_date = None
                    document.issue_body = None
            if document_file:
                document.document_file = document_file
            if issue_date and document_type != 'resume':
                try:
                    # Convert Nepali date to English date
                    english_date = nepali_str_to_english(issue_date)
                    document.issue_date = english_date
                except Exception as e:
                    messages.error(request, f"Invalid date format: {str(e)}")
                    return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")
            if issue_body is not None and document_type != 'resume':
                # Convert issue_body ID to District instance
                if issue_body:
                    try:
                        document.issue_body = District.objects.get(id=issue_body)
                    except District.DoesNotExist:
                        messages.error(request, "Invalid district ID")
                        return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")
                else:
                    document.issue_body = None
            
            document.save()
            messages.success(request, "Document updated successfully.")
            
        except Exception as e:
            messages.error(request, f"Error updating document: {str(e)}")
        
        return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=document")

class DeletePayoutView(View):
    def get(self, request, pk):
        payout = get_object_or_404(Payout, pk=pk)
        user = payout.user
        payout.delete()
        messages.success(request, "Payout deleted successfully.")
        return redirect(f"{reverse('user:employee_edit', kwargs={'pk': user.id})}?tab=payout")

#assign leave to employee
def assignLeaveToEmployee(employee):
    try:
        profile = employee.profile
        working_detail = employee.working_detail
    except (Profile.DoesNotExist, WorkingDetail.DoesNotExist):
        return  # Can't assign without required data

    gender = profile.gender
    marital_status = profile.marital_status
    job_type = working_detail.job_type
    joining_date = working_detail.joining_date
    branch = working_detail.branch
    department = working_detail.department

    if not joining_date:
        return  # Can't assign without joining date

    leave_types = LeaveType.objects.filter(status='active')

    for leave_type in leave_types:
        # Gender match
        if leave_type.gender != 'A' and leave_type.gender != gender:
            continue

        # Marital status match
        if leave_type.marital_status != 'A' and leave_type.marital_status != marital_status:
            continue

        # Job type match
        if leave_type.job_type != 'all' and leave_type.job_type != job_type:
            continue

        # Branch match (skip if not assigned to current branch)
        if leave_type.branches.exists() and branch not in leave_type.branches.all():
            continue

        # Department match (skip if not assigned to current department)
        if leave_type.departments.exists() and department not in leave_type.departments.all():
            continue

        fiscal_year = leave_type.fiscal_year

        # Prorated leave calculation
        if joining_date <= fiscal_year.start_date:
            total_leave = leave_type.number_of_days
        else:
            month_diff = (fiscal_year.end_date - joining_date).days // 30
            if month_diff <= 0:
                continue
            raw_leave = round(month_diff * (leave_type.number_of_days / 12), 1)
            total_leave = point_down_round(raw_leave)

        emp_leave_qs = EmployeeLeave.objects.filter(employee=employee, leave_type=leave_type)

        if emp_leave_qs.exists():
            emp_leave = emp_leave_qs.first()
            emp_leave.total_leave = total_leave
            emp_leave.leave_remaining = max(0, total_leave - emp_leave.leave_taken)
            emp_leave.is_active = True
            emp_leave.updated_by = leave_type.updated_by
            emp_leave.save()
        else:
            EmployeeLeave.objects.create(
                employee=employee,
                leave_type=leave_type,
                total_leave=total_leave,
                leave_taken=0,
                leave_remaining=total_leave,
                created_by=leave_type.created_by,
                updated_by=leave_type.updated_by,
                is_active=True
            )


