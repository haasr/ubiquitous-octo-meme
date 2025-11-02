"""
Views for the Smart Alarm application.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, time
from .models import *
from .forms import RoutineForm, UserProfileForm
from .scheduler import schedule_routine, remove_routine_schedule, reload_all_schedules

def index(request):
    """
    Dashboard view showing active routines and recent activity.
    """
    # Get current time for greeting
    current_hour = timezone.now().hour
    if current_hour < 12:
        greeting_time = "morning"
    elif current_hour < 18:
        greeting_time = "afternoon"
    else:
        greeting_time = "evening"

    # Get user profile
    user_profile = UserProfile.get_profile()

    # Get statistics
    all_routines = Routine.objects.all()
    total_routines = all_routines.count()
    active_routines = all_routines.filter(enabled=True)
    active_routines_count = active_routines.count()

    # Get routines scheduled for today
    routines_today = [r for r in active_routines if r.is_scheduled_today()]

    # Get recent execution logs
    recent_logs = RoutineLog.objects.select_related("routine").order_by(
        "-started_at"
    )[:10]

    # Total executions
    total_executions = RoutineLog.objects.count()

    context = {
        "greeting_time": greeting_time,
        "user_profile": user_profile,
        "total_routines": total_routines,
        "active_routines_count": active_routines_count,
        "routines_today": routines_today,
        "recent_logs": recent_logs,
        "total_executions": total_executions,
    }

    return render(request, "alarm_app/index.html", context)


class RoutineListView(ListView):
    """
    List all routines with filtering options.
    """

    model = Routine
    template_name = "alarm_app/routine_list.html"
    context_object_name = "routines"
    paginate_by = 12

    def get_queryset(self):
        queryset = Routine.objects.all().order_by("-created_at")

        # Filter by status
        status = self.request.GET.get("status")
        if status == "enabled":
            queryset = queryset.filter(enabled=True)
        elif status == "disabled":
            queryset = queryset.filter(enabled=False)

        # Filter by schedule type
        schedule_type = self.request.GET.get("schedule_type")
        if schedule_type in ["once", "recurring"]:
            queryset = queryset.filter(schedule_type=schedule_type)

        return queryset


class RoutineDetailView(DetailView):
    """
    Display detailed information about a routine.
    """

    model = Routine
    template_name = "alarm_app/routine_detail.html"
    context_object_name = "routine"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get execution logs for this routine
        context["logs"] = (
            RoutineLog.objects.filter(routine=self.object)
            .order_by("-started_at")[:20]
        )

        return context


class RoutineCreateView(CreateView):
    """
    Create a new routine.
    """

    model = Routine
    form_class = RoutineForm
    template_name = "alarm_app/routine_form.html"

    def get_success_url(self):
        return reverse_lazy("alarm_app:routine_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Routine '{self.object.name}' created successfully!")

        # Reload scheduler to pick up new routine
        from .scheduler import schedule_routine
        schedule_routine(self.object)

        return response


class RoutineUpdateView(UpdateView):
    """
    Edit an existing routine.
    """

    model = Routine
    form_class = RoutineForm
    template_name = "alarm_app/routine_form.html"

    def get_success_url(self):
        return reverse_lazy("alarm_app:routine_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Routine '{self.object.name}' updated successfully!")

        # Reload scheduler to pick up changes
        from .scheduler import schedule_routine
        schedule_routine(self.object)

        return response


class RoutineDeleteView(DeleteView):
    """
    Delete a routine.
    """

    model = Routine
    success_url = reverse_lazy("alarm_app:routine_list")

    def delete(self, request, *args, **kwargs):
        routine = self.get_object()
        routine_name = routine.name
        routine_id = routine.id

        # Remove from scheduler
        from .scheduler import remove_routine_schedule
        remove_routine_schedule(routine_id)

        response = super().delete(request, *args, **kwargs)
        messages.success(request, f"Routine '{routine_name}' deleted successfully.")

        return response


def routine_toggle(request, pk):
    """
    Toggle routine enabled/disabled status.
    """
    if request.method == "POST":
        routine = get_object_or_404(Routine, pk=pk)
        routine.enabled = not routine.enabled
        routine.save()

        from .scheduler import schedule_routine, remove_routine_schedule
        if routine.enabled:
            schedule_routine(routine)
        else:
            remove_routine_schedule(routine.id)

        status = "enabled" if routine.enabled else "disabled"
        messages.success(request, f"Routine '{routine.name}' {status}.")

        return redirect("alarm_app:routine_detail", pk=pk)

    return redirect("alarm_app:routine_list")


def settings_view(request):
    """
    Settings page for user profile and system configuration.
    """
    profile = UserProfile.get_profile()

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved successfully!")
            return redirect("alarm_app:settings")
    else:
        form = UserProfileForm(instance=profile)

    from django_q.models import Schedule
    scheduler_running = True  # Django-Q is always "running" if installed
    scheduled_jobs_count = Schedule.objects.filter(name__startswith='routine_').count()

    context = {
        "form": form,
        "quote_count": Quote.objects.filter(active=True).count(),
        "news_source_count": NewsSource.objects.filter(active=True).count(),
        "location_count": WeatherLocation.objects.count(),
        "audio_count": AudioFile.objects.count(),
        "scheduler_running": scheduler_running,
        "scheduled_jobs_count": scheduled_jobs_count,
        "total_executions": RoutineLog.objects.count(),
    }

    return render(request, "alarm_app/settings.html", context)
