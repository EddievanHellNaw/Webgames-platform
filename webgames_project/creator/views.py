from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def creator_dashboard(request):
    return render(
        request,
        "creator/dashboard.html",
    )