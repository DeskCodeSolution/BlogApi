from django.contrib import admin
from django.urls import path, include
from .views import *

urlpatterns = [
   path('register/', UserRegisterView.as_view()),
   path('login/', UserLoginView.as_view()),

   path('post/',  PostsListCreateView.as_view()),
   path('post/<int:pk>/', PostsDetailView.as_view()),

   path('post/comment/', CommentCreateView.as_view()),
   path('post/category/', CategoryCreateView.as_view()),
   path('post/category/<str:name>/', CategoryPostList.as_view()),

]
