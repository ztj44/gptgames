from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("", views.home, name="home"),
    path("new_character/", views.submit_character_prompt, name="new_character"),
    path("review_character/", views.review_character, name="review_character"),
    path("choose_monsters/", views.choose_monsters, name="choose_monsters"),
    path("arena/", views.arena, name="arena"),
    path("defeat/<int:winner_id>/<int:loser_id>/", views.defeat, name="defeat_page"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
