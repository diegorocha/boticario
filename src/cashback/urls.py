from django.urls import path, include

from cashback.api import v1_router

urlpatterns = [
    path('v1/', include(v1_router.urls)),
]
