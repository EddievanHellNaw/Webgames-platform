# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import GameTemplate


@login_required
def teacher_dashboard(request):
    games = GameTemplate.objects.filter(is_active=True)

    return render(
        request,
        "games/teacher_dashboard.html",
        {
            "games": games,
        },
    )